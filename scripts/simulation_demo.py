#!/usr/bin/env python3
"""
MetaKG Simulation Demo Script

Demonstrate metabolic pathway simulation capabilities:
- Flux Balance Analysis (FBA) for steady-state flux prediction
- Kinetic ODE simulation for time-course dynamics
- What-if perturbation analysis for enzyme knockouts and modifications

Usage:
    poetry run python scripts/simulation_demo.py

This script assumes metakg-build --data ./pathways has been run already.
"""

import sys
from pathlib import Path
import json

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from metakg import MetaKG


def demo_1_seed_kinetics():
    """Demo 1: Seed kinetic parameters from BRENDA/SABIO-RK."""
    print("\n" + "=" * 80)
    print("Demo 1: Seeding Kinetic Parameters")
    print("=" * 80)
    print("""
from metakg import MetaKG

kg = MetaKG()

# Seed the database with curated kinetic parameters from literature
# (BRENDA, SABIO-RK, metabolic models)
result = kg.seed_kinetics()

print(f"Kinetic parameters written: {result['kinetic_params_written']}")
print(f"Regulatory interactions: {result['regulatory_interactions_written']}")

kg.close()
""")

    kg = MetaKG()
    print("\n--- Output ---")

    try:
        result = kg.seed_kinetics()
        print(f"Kinetic parameters written: {result.get('kinetic_params_written', '?')}")
        print(f"Regulatory interactions: {result.get('regulatory_interactions_written', '?')}")
    except Exception as e:
        print(f"(seed_kinetics not yet available: {e})")

    kg.close()


def demo_2_fba_glycolysis():
    """Demo 2: Flux Balance Analysis on glycolysis pathway."""
    print("\n" + "=" * 80)
    print("Demo 2: Flux Balance Analysis - Glycolysis")
    print("=" * 80)
    print("""
from metakg import MetaKG

kg = MetaKG()

# Run FBA on glycolysis pathway to find steady-state flux distribution
# Maximizes overall ATP production (default objective)
result = kg.simulate_fba(
    pathway_id="Glycolysis",  # or pwy:kegg:hsa00010
    maximize=True
)

print(f"Status: {result['status']}")
print(f"Objective value: {result['objective_value']:.3f}")
print(f"Number of reactions: {len(result['fluxes'])}")

# Show top 5 fluxes by absolute magnitude
fluxes_sorted = sorted(
    result['fluxes'].items(),
    key=lambda x: abs(x[1]),
    reverse=True
)
for rxn_id, flux in fluxes_sorted[:5]:
    print(f"  {rxn_id:40s}  v = {flux:8.3f}")

kg.close()
""")

    kg = MetaKG()
    print("\n--- Output ---")

    try:
        result = kg.simulate_fba(pathway_id="Glycolysis", maximize=True)
        print(f"Status: {result.get('status', '?')}")
        print(f"Objective value: {result.get('objective_value', '?')}")

        fluxes = result.get('fluxes', {})
        print(f"Number of reactions: {len(fluxes)}")

        if fluxes:
            print("\n# Top 5 fluxes (by absolute magnitude):")
            fluxes_sorted = sorted(
                fluxes.items(),
                key=lambda x: abs(x[1]),
                reverse=True
            )
            for rxn_id, flux in fluxes_sorted[:5]:
                print(f"  {str(rxn_id):40s}  v = {flux:8.3f}")
        else:
            print("(no flux data)")
    except Exception as e:
        print(f"(FBA not available or pathway not found: {e})")

    kg.close()


def demo_3_fba_with_objective():
    """Demo 3: FBA with specific reaction as objective."""
    print("\n" + "=" * 80)
    print("Demo 3: FBA with Custom Objective")
    print("=" * 80)
    print("""
from metakg import MetaKG

kg = MetaKG()

# Run FBA optimizing for a specific reaction (e.g., ATP synthesis)
result = kg.simulate_fba(
    pathway_id="Glycolysis",
    objective_reaction="kegg:R00015",  # Phosphoglycerate kinase (ATP producer)
    maximize=True
)

print(f"Status: {result['status']}")
print(f"Objective flux: {result['objective_value']:.3f} mM/s")

kg.close()
""")

    kg = MetaKG()
    print("\n--- Output ---")

    try:
        # Try to get a specific ATP-producing reaction from glycolysis
        result = kg.simulate_fba(
            pathway_id="Glycolysis",
            objective_reaction="kegg:R00015",
            maximize=True
        )
        print(f"Status: {result.get('status', '?')}")
        obj_val = result.get('objective_value', '?')
        if isinstance(obj_val, (int, float)):
            print(f"Objective flux: {obj_val:.3f} mM/s")
        else:
            print(f"Objective flux: {obj_val}")
    except Exception as e:
        print(f"(Custom objective FBA not available: {e})")

    kg.close()


def demo_4_ode_simulation():
    """Demo 4: Kinetic ODE simulation for time-course dynamics."""
    print("\n" + "=" * 80)
    print("Demo 4: Kinetic ODE Simulation - Time-Course Dynamics")
    print("=" * 80)
    print("""
from metakg import MetaKG
import json

kg = MetaKG()

# Simulate glycolysis over time with Michaelis-Menten kinetics
# Initial glucose = 5 mM, ATP = 3 mM, other compounds = 1 mM
initial_conc = {
    "cpd:kegg:C00031": 5.0,  # D-Glucose
    "cpd:kegg:C00002": 3.0,  # ATP
}

result = kg.simulate_ode(
    pathway_id="Glycolysis",
    t_end=100,           # Simulate to t=100
    t_points=50,         # 50 time points
    initial_concentrations_json=json.dumps(initial_conc),
    default_concentration=1.0
)

print(f"Status: {result['status']}")
print(f"Time points: {len(result['t'])}")
print(f"Compounds tracked: {len(result['concentrations'])}")

# Show final concentrations for first 3 compounds
compound_ids = list(result['concentrations'].keys())[:3]
print(f"\\nFinal concentrations:")
for cpd_id in compound_ids:
    conc_array = result['concentrations'][cpd_id]
    if conc_array:
        print(f"  {cpd_id}: {conc_array[-1]:.3f} mM")

kg.close()
""")

    kg = MetaKG()
    print("\n--- Output ---")

    try:
        initial_conc = {
            "cpd:kegg:C00031": 5.0,
            "cpd:kegg:C00002": 3.0,
        }
        result = kg.simulate_ode(
            pathway_id="Glycolysis",
            t_end=100,
            t_points=50,
            initial_concentrations_json=json.dumps(initial_conc),
            default_concentration=1.0
        )

        print(f"Status: {result.get('status', '?')}")
        t = result.get('t', [])
        concs = result.get('concentrations', {})
        print(f"Time points: {len(t)}")
        print(f"Compounds tracked: {len(concs)}")

        if concs:
            print(f"\nFinal concentrations (first 3):")
            for cpd_id in list(concs.keys())[:3]:
                conc_array = concs[cpd_id]
                if conc_array:
                    print(f"  {cpd_id}: {conc_array[-1]:.3f} mM")
        else:
            print("(no concentration data)")
    except Exception as e:
        print(f"(ODE simulation not available: {e})")

    kg.close()


def demo_5_whatif_enzyme_knockout():
    """Demo 5: What-if analysis - enzyme knockout perturbation."""
    print("\n" + "=" * 80)
    print("Demo 5: What-If Analysis - Enzyme Knockout")
    print("=" * 80)
    print("""
from metakg import MetaKG
import json

kg = MetaKG()

# What-if: knock out hexokinase (enzyme that phosphorylates glucose)
# This is a key control point in glycolysis
scenario = {
    "name": "hexokinase_knockout",
    "enzyme_knockouts": ["enz:kegg:hsa:2539"]  # Hexokinase
}

result = kg.simulate_whatif(
    pathway_id="Glycolysis",
    scenario_json=json.dumps(scenario),
    mode="fba"
)

print(f"Baseline objective: {result['baseline']['objective_value']:.3f}")
print(f"Perturbed objective: {result['perturbed']['objective_value']:.3f}")
print(f"Change: {result['perturbed']['objective_value'] - result['baseline']['objective_value']:.3f}")

# Show top affected reactions
if result.get('delta_fluxes'):
    deltas = sorted(
        result['delta_fluxes'].items(),
        key=lambda x: abs(x[1]),
        reverse=True
    )
    print(f"\\nTop 3 affected reactions:")
    for rxn_id, delta in deltas[:3]:
        print(f"  {rxn_id:40s}  Δv = {delta:8.3f}")

kg.close()
""")

    kg = MetaKG()
    print("\n--- Output ---")

    try:
        scenario = {
            "name": "hexokinase_knockout",
            "enzyme_knockouts": ["enz:kegg:hsa:2539"]
        }
        result = kg.simulate_whatif(
            pathway_id="Glycolysis",
            scenario_json=json.dumps(scenario),
            mode="fba"
        )

        baseline_obj = result.get('baseline', {}).get('objective_value', '?')
        perturbed_obj = result.get('perturbed', {}).get('objective_value', '?')

        print(f"Baseline objective: {baseline_obj}")
        print(f"Perturbed objective: {perturbed_obj}")

        if isinstance(baseline_obj, (int, float)) and isinstance(perturbed_obj, (int, float)):
            print(f"Change: {perturbed_obj - baseline_obj:.3f}")

        delta_fluxes = result.get('delta_fluxes', {})
        if delta_fluxes:
            print(f"\nTop 3 affected reactions:")
            deltas = sorted(
                delta_fluxes.items(),
                key=lambda x: abs(x[1]),
                reverse=True
            )
            for rxn_id, delta in deltas[:3]:
                print(f"  {str(rxn_id):40s}  Δv = {delta:8.3f}")
    except Exception as e:
        print(f"(What-if analysis not available: {e})")

    kg.close()


def demo_6_whatif_enzyme_inhibition():
    """Demo 6: What-if analysis - partial enzyme inhibition."""
    print("\n" + "=" * 80)
    print("Demo 6: What-If Analysis - Enzyme Inhibition (50%)")
    print("=" * 80)
    print("""
from metakg import MetaKG
import json

kg = MetaKG()

# What-if: inhibit phosphofructokinase (PFK) to 50% activity
# PFK is the key committed step and main control point in glycolysis
scenario = {
    "name": "pfk_inhibition_50pct",
    "enzyme_factors": {
        "enz:kegg:hsa:2671": 0.5  # PFK activity reduced to 50%
    }
}

result = kg.simulate_whatif(
    pathway_id="Glycolysis",
    scenario_json=json.dumps(scenario),
    mode="fba"
)

baseline = result['baseline']['objective_value']
perturbed = result['perturbed']['objective_value']
percent_change = 100 * (perturbed - baseline) / baseline if baseline != 0 else 0

print(f"Baseline ATP: {baseline:.3f}")
print(f"With 50% PFK: {perturbed:.3f}")
print(f"Change: {percent_change:.1f}%")

kg.close()
""")

    kg = MetaKG()
    print("\n--- Output ---")

    try:
        scenario = {
            "name": "pfk_inhibition_50pct",
            "enzyme_factors": {
                "enz:kegg:hsa:2671": 0.5
            }
        }
        result = kg.simulate_whatif(
            pathway_id="Glycolysis",
            scenario_json=json.dumps(scenario),
            mode="fba"
        )

        baseline = result.get('baseline', {}).get('objective_value', 0)
        perturbed = result.get('perturbed', {}).get('objective_value', 0)

        print(f"Baseline ATP: {baseline:.3f}")
        print(f"With 50% PFK: {perturbed:.3f}")

        if baseline != 0:
            percent_change = 100 * (perturbed - baseline) / baseline
            print(f"Change: {percent_change:.1f}%")
    except Exception as e:
        print(f"(Enzyme inhibition analysis not available: {e})")

    kg.close()


def main():
    """Run all simulation demos."""
    print("\n" + "#" * 80)
    print("# MetaKG Simulation Demos")
    print("#" * 80)
    print("\nDemonstrating simulation and perturbation capabilities:")
    print("  - Flux Balance Analysis (FBA)")
    print("  - Kinetic ODE simulation")
    print("  - What-if perturbation analysis")
    print("\nAssumes: metakg-build --data ./pathways has been run")

    try:
        demo_1_seed_kinetics()
        demo_2_fba_glycolysis()
        demo_3_fba_with_objective()
        demo_4_ode_simulation()
        demo_5_whatif_enzyme_knockout()
        demo_6_whatif_enzyme_inhibition()

        print("\n" + "#" * 80)
        print("# Simulation demos complete")
        print("#" * 80 + "\n")

    except Exception as e:
        import traceback
        print(f"\nError: {e}")
        traceback.print_exc()
        print("\nMake sure you've run: poetry run metakg-build --data ./pathways")
        sys.exit(1)


if __name__ == "__main__":
    main()
