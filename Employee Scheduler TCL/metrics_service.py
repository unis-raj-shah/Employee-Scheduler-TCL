"""Service for warehouse metrics calculations."""

from typing import Dict, Any
from config import DEFAULT_METRICS, WORKFORCE_EFFICIENCY, HOURS_PER_SHIFT

def get_metrics_summary() -> Dict[str, Dict[str, float]]:
    """
    Return metrics summaries.
    
    Returns:
        Dictionary of metrics by operation type
    """
    return DEFAULT_METRICS

def calculate_required_roles(metrics_summaries: Dict[str, Dict[str, float]],
                            forecast_data: Dict[str, Any]) -> Dict[str, Dict[str, int]]:
    """
    Calculate required roles based on metrics and forecast data.
    
    Args:
        metrics_summaries: Dictionary of metrics by operation type
        forecast_data: Dictionary containing forecast data
        
    Returns:
        Dictionary of required role counts by operation
    """
    try:
        incoming_pallets = forecast_data.get("daily_incoming_pallets", 0)
        shipping_pallets = forecast_data.get("daily_shipping_pallets", 0)
        total_cases = forecast_data.get("daily_order_qty", 0)
        cases_to_pick = forecast_data.get("cases_to_pick", 0)
        staged_pallets = forecast_data.get("staged_pallets", 0)
        
        final_roles = {
            "inbound": {"forklift_driver": 0, "receiver": 0, "lumper": 0},
            "picking": {"forklift_driver": 0},
            "loading": {"forklift_driver": 0},
            "replenishment": {"staff": 0}
        }
        
        effective_work_mins_per_person = HOURS_PER_SHIFT * 60 * WORKFORCE_EFFICIENCY
        calculated_shipping_pallets = total_cases/24
        shipping_pallets = shipping_pallets + calculated_shipping_pallets
        
        # Calculate inbound operations requirements
        if "inbound" in metrics_summaries and incoming_pallets > 0:
            inbound = metrics_summaries["inbound"]
            total_offload_time = incoming_pallets * inbound.get("avg_offload_time", 3.0)
            total_scan_time = incoming_pallets * inbound.get("avg_scan_time", 0.15)
            total_putaway_time = incoming_pallets * inbound.get("avg_putaway_time", 2.5)
            total_lumper_time = incoming_pallets * inbound.get("avg_lumper_time", 2.5)
            
            # Calculate forklift drivers needed for inbound (offload + putaway)
            inbound_forklift = min(5, round(total_offload_time / effective_work_mins_per_person))
            putaway_forklift = min(3, round(total_putaway_time / effective_work_mins_per_person))
            final_roles["inbound"]["forklift_driver"] = inbound_forklift + putaway_forklift
            
            # Calculate receivers and lumpers
            final_roles["inbound"]["receiver"] = max(1, round(total_scan_time / effective_work_mins_per_person))
            final_roles["inbound"]["lumper"] = min(5, round(total_lumper_time / effective_work_mins_per_person))

        # Calculate picking operations requirements
        if "picking" in metrics_summaries:
            picking = metrics_summaries["picking"]
            
            # Only calculate picking requirements if there are cases to pick
            if cases_to_pick > 0:
                total_pick_time = cases_to_pick * picking.get("avg_pick_time", 1.0)
                total_wrap_time = calculated_shipping_pallets * picking.get("avg_wrap_time", 2.5)
                

                # Calculate forklift drivers needed for picking
                pick_forklift = max(1, round(total_pick_time / effective_work_mins_per_person))
                wrap_forklift = max(1, round(total_wrap_time / effective_work_mins_per_person))
                final_roles["picking"]["forklift_driver"] = pick_forklift + wrap_forklift
                
            else:
                final_roles["picking"]["forklift_driver"] = 0
        
        # Calculate loading requirements for staged pallets
        if "load" in metrics_summaries:
            load = metrics_summaries["load"]
            load_time_per_pallet = load.get("avg_load_time_per_pallet", 3.75)
            
            # Calculate loading time for staged pallets
            if staged_pallets:
                staged_load_time = staged_pallets * load_time_per_pallet
                final_roles["loading"]["forklift_driver"] = max(1, round(staged_load_time / effective_work_mins_per_person))
            
            # Calculate loading time for forecasted shipping pallets (non-picked)
            if shipping_pallets > 0:
                forecast_load_time = shipping_pallets * load_time_per_pallet
                final_roles["loading"]["forklift_driver"] += max(1, round(forecast_load_time / effective_work_mins_per_person))
        
        # Calculate total headcount and consolidation
        total_headcount = (
            final_roles["inbound"]["forklift_driver"] +
            final_roles["inbound"]["lumper"] +
            final_roles["inbound"]["receiver"] +
            final_roles["picking"]["forklift_driver"] +
            final_roles["loading"]["forklift_driver"]
        )
        
        final_roles["replenishment"]["staff"] = max(1, round(total_headcount * 0.1))
        
        
        return final_roles
        
    except Exception as e:
        print(f"Error in calculate_required_roles: {str(e)}")
        return {
            "inbound": {"forklift_driver": 3, "receiver": 2, "lumper": 3},
            "picking": {"forklift_driver": 2},
            "loading": {"forklift_driver": 2},
            "replenishment": {"staff": 1}
        }