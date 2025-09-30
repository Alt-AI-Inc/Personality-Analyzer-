#!/usr/bin/env python3

"""
Estimate cost and time for faceted personality assessment
"""

def estimate_assessment(model="gpt-4o-mini", facets="both", rpm=15):
    """Estimate cost and time for assessment"""
    
    # Token estimates based on actual usage patterns
    estimates = {
        "gpt-4o-mini": {
            "p2_generation": {"input": 7000, "output": 3000, "cost_per_1k_in": 0.00015, "cost_per_1k_out": 0.0006},
            "bfi_question": {"input": 600, "output": 150, "cost_per_1k_in": 0.00015, "cost_per_1k_out": 0.0006}
        },
        "gpt-4o": {
            "p2_generation": {"input": 7000, "output": 3000, "cost_per_1k_in": 0.0025, "cost_per_1k_out": 0.01},
            "bfi_question": {"input": 600, "output": 150, "cost_per_1k_in": 0.0025, "cost_per_1k_out": 0.01}
        },
        "gpt-5": {
            "p2_generation": {"input": 7000, "output": 3000, "cost_per_1k_in": 0.03, "cost_per_1k_out": 0.12},
            "bfi_question": {"input": 600, "output": 300, "cost_per_1k_in": 0.03, "cost_per_1k_out": 0.12}  # More tokens for reasoning
        }
    }
    
    if model not in estimates:
        print(f"❌ Unknown model: {model}")
        return
    
    model_rates = estimates[model]
    
    # Calculate requests and costs
    if facets == "both":
        p2_requests = 2  # Personal + Professional
        bfi_requests = 120  # 60 questions × 2 facets
    elif facets in ["personal", "professional"]:
        p2_requests = 1
        bfi_requests = 60
    else:
        print(f"❌ Invalid facets: {facets}")
        return
    
    # P2 Generation Cost
    p2_cost = 0
    for _ in range(p2_requests):
        p2_in_cost = (model_rates["p2_generation"]["input"] / 1000) * model_rates["p2_generation"]["cost_per_1k_in"]
        p2_out_cost = (model_rates["p2_generation"]["output"] / 1000) * model_rates["p2_generation"]["cost_per_1k_out"]
        p2_cost += p2_in_cost + p2_out_cost
    
    # BFI Questions Cost
    bfi_cost = 0
    for _ in range(bfi_requests):
        bfi_in_cost = (model_rates["bfi_question"]["input"] / 1000) * model_rates["bfi_question"]["cost_per_1k_in"]
        bfi_out_cost = (model_rates["bfi_question"]["output"] / 1000) * model_rates["bfi_question"]["cost_per_1k_out"]
        bfi_cost += bfi_in_cost + bfi_out_cost
    
    total_cost = p2_cost + bfi_cost
    total_requests = p2_requests + bfi_requests
    
    # Time estimation
    estimated_time_minutes = (total_requests / rpm) * 60 / 60  # Convert to minutes
    
    # Display results
    print(f"📊 Assessment Estimation for {model.upper()}")
    print(f"=" * 50)
    print(f"Facets: {facets}")
    print(f"Rate limit: {rpm} requests/minute")
    print()
    print(f"🔢 Request Breakdown:")
    print(f"   P2 Generation: {p2_requests} requests")
    print(f"   BFI Questions: {bfi_requests} requests")
    print(f"   Total: {total_requests} requests")
    print()
    print(f"💰 Cost Breakdown:")
    print(f"   P2 Generation: ${p2_cost:.4f}")
    print(f"   BFI Questions: ${bfi_cost:.4f}")
    print(f"   Total Cost: ${total_cost:.4f}")
    print()
    print(f"⏱️  Time Estimate:")
    print(f"   At {rpm} req/min: {estimated_time_minutes:.1f} minutes")
    print()
    
    # Recommendations
    if model == "gpt-5":
        print(f"⚠️  GPT-5 Notes:")
        print(f"   - Much slower due to reasoning overhead")
        print(f"   - Individual questions may take 5-10 seconds each")
        print(f"   - Consider using gpt-4o-mini for initial testing")
        print()
    
    if total_cost > 1.0:
        print(f"💡 Cost Optimization Tips:")
        print(f"   - Use gpt-4o-mini for testing (20x cheaper)")
        print(f"   - Run single facet first to validate")
        print(f"   - Consider batching if model supports it")
    
    print(f"🚀 Recommended Command:")
    if total_cost > 0.5:
        print(f"   python3 bfi_probe_rate_limited.py --model gpt-4o-mini --facet {facets} --rpm {max(10, rpm//2)}")
    else:
        print(f"   python3 bfi_probe_rate_limited.py --model {model} --facet {facets} --rpm {rpm}")

if __name__ == "__main__":
    import argparse
    
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gpt-4o-mini", choices=["gpt-4o-mini", "gpt-4o", "gpt-5"])
    ap.add_argument("--facets", default="both", choices=["personal", "professional", "both"])
    ap.add_argument("--rpm", type=int, default=15, help="Requests per minute")
    
    args = ap.parse_args()
    
    estimate_assessment(args.model, args.facets, args.rpm)