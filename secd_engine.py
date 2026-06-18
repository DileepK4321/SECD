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
    # 1. Calculate current line flows using: calculate_line_flows(dispatch, ptdf_matrix)
    calculated_flows = calculate_line_flows(dispatch, ptdf_matrix)
    # 2. Check if Line_2-3 (Index 1 in your matrix) exceeds its normal_limit (50 MW)
    while abs(calculated_flows[1]) > 50:
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
    