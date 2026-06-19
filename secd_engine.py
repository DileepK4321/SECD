import json
import numpy as np

def load_market_data(filepath="sced_config.json"):
    """Loads the grid configuration and generator data."""
    with open(filepath, "r") as file:
        return json.load(file)

def calculate_unconstrained_lambda(generators, total_load):
    """Calculates the baseline system lambda using incremental cost curves."""
    numerator_sum = 0
    denominator_sum = 0
    
    for gen in generators:
        numerator_sum += gen["b"] / (2 * gen["a"])
        denominator_sum += 1 / (2 * gen["a"])
        
    system_lambda = (total_load + numerator_sum) / denominator_sum
    return system_lambda

def dispatch_generators(generators, system_lambda):
    """Dispatches individual units based on system lambda and clamps to limits."""
    dispatch_results = {}
    for gen in generators:
        p_calc = (system_lambda - gen["b"]) / (2 * gen["a"])
        
        # Enforce physical P_min and P_max constraints
        p_dispatched = max(gen["p_min"], min(p_calc, gen["p_max"]))
        dispatch_results[gen["id"]] = p_dispatched
        
    return dispatch_results

def calculate_line_flows(dispatch_results, ptdf_matrix):
    """
    Uses the PTDF matrix to map generator outputs to physical transmission line flows.
    Formula: Flow = PTDF * Generation_Vector
    """
    # Convert dispatch dictionary to a clean NumPy vector [Gen1, Gen2, Gen3]
    gen_vector = np.array([
        dispatch_results[1],
        dispatch_results[2],
        dispatch_results[3]
    ])
    
    # Compute physical line flows using matrix-vector multiplication
    line_flows = np.dot(ptdf_matrix, gen_vector)
    return line_flows

def optimize_sced_network(generators, initial_dispatch, ptdf_matrix, config):
    """
    Your Task: Write the optimization loop to eliminate line overloads.
    
    Inputs:
      - generators: The list of gen dictionaries (to get a, b, limits)
      - initial_dispatch: Dictionary of current MW dispatches {1: MW, 2: MW, 3: MW}
      - ptdf_matrix: NumPy matrix for network flows
      - config: Complete JSON configuration (to get transmission limits)
    """
    dispatch = initial_dispatch.copy()
    line_names = [line["id"] for line in config["transmission_lines"]]
    normal_limits = [line["normal_limit"] for line in config["transmission_lines"]]
    
    # --- START YOUR LOGIC HERE ---
    line_2_3_limit = config["transmission_lines"][1]["normal_limit"]
    # 1. Calculate current line flows using: calculate_line_flows(dispatch, ptdf_matrix)
    calculated_flows = calculate_line_flows(dispatch, ptdf_matrix)
    # 2. Check if Line_2-3 (Index 1 in your matrix) exceeds its normal_limit (50 MW)
    while abs(calculated_flows[1]) > line_2_3_limit:
        dispatch[2] -=1.0
        dispatch[3] +=1.0
        calculated_flows = calculate_line_flows(dispatch, ptdf_matrix)
    # 3. If it does, reduce dispatch[1] (Gen 2) and increase dispatch[2] (Gen 3) 
    #    while maintaining Total Load = 250 MW.
    # 4. Loop until the flow on Line_2-3 is <= 50 MW.

    # Hint: For every 1 MW you drop from Gen 2, you must add 1 MW to Gen 3 to balance load.
    # How does that 1 MW shift change the flow on Line_2-3? 
    # Look at the PTDF row for Line_2-3: Gen 2 factor is 0.6, Gen 3 factor is 0.0.
    # Net flow change per MW shifted = (0.0 - 0.6) = -0.6 MW!
    
    # --- END YOUR LOGIC HERE ---
    
    return dispatch

def run_n_1_contingency_analysis(current_flows, config):
    """
    Simulates N-1 line outages and automatically flags limit violations.
    """
    print("\n==================================================")
    print("   RUNNING AUTOMATED N-1 CONTINGENCY SECURITY SCAN")
    print("==================================================")
    
    limits = {
        0: {"name": "Line_1-2", "normal": config["transmission_lines"][0]["normal_limit"], "emergency": config["transmission_lines"][0]["emergency_limit"]},
        1: {"name": "Line_2-3", "normal": config["transmission_lines"][1]["normal_limit"], "emergency": config["transmission_lines"][1]["emergency_limit"]},
        2: {"name": "Line_1-3", "normal": config["transmission_lines"][2]["normal_limit"], "emergency": config["transmission_lines"][2]["emergency_limit"]}
    }
    
    f12, f23, f13 = current_flows[0], current_flows[1], current_flows[2]
    system_secure = True  # Flag to track overall grid security status
    
    # --- CONTINGENCY 1: LINE 1-2 TRIPS ---
    print("\nSimulating Outage of: Line_1-2...")
    post_f23 = abs(f23 - f12)
    post_f13 = abs(f13 + f12)
    
    if post_f23 > limits[1]["emergency"] or post_f13 > limits[2]["emergency"]:
        print("   SYSTEM ALERT: EMERGENCY LIMIT VIOLATION DETECTED!")
        system_secure = False
    elif post_f23 > limits[1]["normal"] or post_f13 > limits[2]["normal"]:
        print("   WARNING: Normal limit exceeded, but within Emergency buffer.")
    else:
        print("  Secure: Remaining lines can comfortably handle the shift.")

    # --- CONTINGENCY 2: LINE 2-3 TRIPS ---
    print("\nSimulating Outage of: Line_2-3...")
    post_f12 = abs(f12 - f23)
    post_f13 = abs(f13 + f23)
    
    if post_f12 > limits[0]["emergency"] or post_f13 > limits[2]["emergency"]:
        print("   SYSTEM ALERT: EMERGENCY LIMIT VIOLATION DETECTED!")
        system_secure = False
    elif post_f12 > limits[0]["normal"] or post_f13 > limits[2]["normal"]:
        print("   WARNING: Normal limit exceeded, but within Emergency buffer.")
    else:
        print("   Secure: Remaining lines can comfortably handle the shift.")
        
    # --- CONTINGENCY 3: LINE 1-3 TRIPS ---
    print("\nSimulating Outage of: Line_1-3...")
    post_f12 = abs(f12 + f13)
    post_f23 = abs(f23 + f13)
    
    if post_f12 > limits[0]["emergency"] or post_f23 > limits[1]["emergency"]:
        print("   SYSTEM ALERT: EMERGENCY LIMIT VIOLATION DETECTED!")
        system_secure = False
    elif post_f12 > limits[0]["normal"] or post_f23 > limits[1]["normal"]:
        print("   WARNING: Normal limit exceeded, but within Emergency buffer.")
    else:
        print("   Secure: Remaining lines can comfortably handle the shift.")

    # Final summary readout
    print("\n================================================== ")
    if system_secure:
        print("  GRID STATUS: N-1 SECURE ")
    else:
        print("  GRID STATUS: N-1 INSECURE  (Mitigation Required)")
    print("==================================================")
    
    return system_secure

def optimize_preventative_sced(generators, initial_dispatch, ptdf_matrix, config):
    """
    Proactively shifts generation to ensure the grid is safe even IF a line trips.
    """
    dispatch = initial_dispatch.copy()
    
    # 1. Calculate the base line flows for our current dispatch
    current_flows = calculate_line_flows(dispatch, ptdf_matrix)
    
    # 2. Extract the emergency limit for Line 2-3 (which is index 1)
    line_2_3_emergency_limit = config["transmission_lines"][1]["emergency_limit"] # 75 MW
    
    # Simulate the contingency flow upfront: post-contingency flow = Line 2-3 flow + Line 1-3 flow
    post_contingency_flow = abs(current_flows[1] + current_flows[2])
    
    # 3. Keep shifting generation as long as the N-1 contingency violates the emergency limit
    while post_contingency_flow > line_2_3_emergency_limit:
        
        # Proactively shift power: Reduce Gen 1 (reduces line stress), pick up slack on Gen 3
        dispatch[1] -= 1.0
        dispatch[3] += 1.0
        
        # Recalculate base flows with the adjusted dispatch
        current_flows = calculate_line_flows(dispatch, ptdf_matrix)
        
        # Recalculate what the emergency flow would be if Line 1-3 tripped right now
        post_contingency_flow = abs(current_flows[1] + current_flows[2])
        
    return dispatch

def calculate_locational_prices(base_lambda, shadow_price, ptdf_matrix):
    """
    Calculates LMPs for all buses based on marginal energy and congestion costs.
    """
    # The baseline energy cost is identical at all buses
    energy_component = base_lambda
    
    # Extract the PTDF row for the bottleneck line (Line_2-3 is index 1)
    # Row 1 contains the impacts for Bus 1, Bus 2, and Bus 3
    line_2_3_ptdfs = ptdf_matrix[1] # [0.4, 0.6, 0.0]
    
    lmps = {}
    
    # Calculate LMP for each Bus (1, 2, and 3)
    # Formula: LMP = Energy_Component - (PTDF * Shadow_Price)
    lmps[1] = energy_component - (line_2_3_ptdfs[0] * shadow_price)
    lmps[2] = energy_component - (line_2_3_ptdfs[1] * shadow_price)
    lmps[3] = energy_component - (line_2_3_ptdfs[2] * shadow_price)
    
    return lmps

if __name__ == "__main__":
    config = load_market_data()
    total_load = config["system_load"]
    generators = config["generators"]
    
    # 1. Define PTDF Matrix (Lines as Rows: 1-2, 2-3, 1-3 | Buses as Cols: 1, 2, 3)
    ptdf_matrix = np.array([
        [ 0.6, -0.4,  0.0],  # Line_1-2
        [ 0.4,  0.6,  0.0],  # Line_2-3
        [ 0.4,  0.4,  0.0]   # Line_1-3
    ])
    
    # 2. Run initial unconstrained economic dispatch
    base_lambda = calculate_unconstrained_lambda(generators, total_load)
    initial_dispatch = dispatch_generators(generators, base_lambda)
    
    print("--- SCED Stage 1: Unconstrained Baseline ---")
    print(f"System Market Clearing Lambda: ${base_lambda:.2f}/MWh\n")
    
    # 3. Calculate and display physical line flows
    calculated_flows = calculate_line_flows(initial_dispatch, ptdf_matrix)
    
    line_names = [line["id"] for line in config["transmission_lines"]]
    normal_limits = [line["normal_limit"] for line in config["transmission_lines"]]
    
    print("--- SCED Stage 2: Physical Network Flow Tracking ---")
    for name, flow, limit in zip(line_names, calculated_flows, normal_limits):
        status = "OK" if abs(flow) <= limit else "⚠️ OVERLOADED"
        print(f"  {name}: Flow = {flow:.2f} MW | Limit = {limit} MW [{status}]")

    # 4. final dispatch
    final_dispatch = optimize_sced_network(generators,initial_dispatch,ptdf_matrix,config)
    final_line_flow = calculate_line_flows(final_dispatch,ptdf_matrix)

    # --- PRINTING THE SECURITY-CONSTRAINED RESULTS ---
    print("\n--- SCED Stage 3: Security-Constrained Re-Dispatch (Solved) ---")
    print("New Corrected Generator Dispatches:")
    for gen_id, mw in final_dispatch.items():
        print(f"  Generator {gen_id}: {mw:.2f} MW")
        
    print("\nNew Physical Line Flows:")
    line_names = [line["id"] for line in config["transmission_lines"]]
    normal_limits = [line["normal_limit"] for line in config["transmission_lines"]]
    
    for name, flow, limit in zip(line_names, final_line_flow, normal_limits):
        status = "OK" if abs(flow) <= limit else "⚠️ OVERLOADED"
        print(f"  {name}: Flow = {flow:.2f} MW | Limit = {limit} MW [{status}]")
    
    #run contingency analysis
    run_n_1_contingency_analysis(final_line_flow,config)

    # 4. Run the preventative re-dispatch optimization
    final_preventative_dispatch = optimize_preventative_sced(generators, final_dispatch, ptdf_matrix, config)
    
    # 5. Calculate the new secure line flows
    secure_line_flows = calculate_line_flows(final_preventative_dispatch, ptdf_matrix)
    
    print("\n==================================================")
    print("   STAGE 4: PREVENTATIVE RE-DISPATCH COMPLETED")
    print("==================================================")
    print("New Proactive Secure Dispatches:")
    for gen_id, mw in final_preventative_dispatch.items():
        print(f"  Generator {gen_id}: {mw:.2f} MW")
        
    # 6. Re-run the security scan to verify the grid is 100% secure now!
    run_n_1_contingency_analysis(secure_line_flows, config)

    # 7. Calculate and display Locational Marginal Prices (LMPs)
    shadow_price = 33.33  # Calculated from our generator cost divergence
    bus_prices = calculate_locational_prices(base_lambda, shadow_price, ptdf_matrix)
    
    print("\n==================================================")
    print("   STAGE 5: LOCATIONAL MARGINAL PRICING (LMP)     ")
    print("==================================================")
    print("Real-Time Locational Electricity Prices:")
    for bus_id, price in bus_prices.items():
        print(f"  Bus {bus_id} LMP: ${price:.2f} / MWh")
    print("==================================================")