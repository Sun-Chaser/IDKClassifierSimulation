from RandomClassifierSetGenerator import RandomSetGenerator 
from DPSimulation import DPSimulation


if __name__ == "__main__":
    M = 5
    N = 100
    generator = RandomSetGenerator(M, N, seed=42)
    probability_matrix, cost_matrix = generator.generate_sets()
    # print("Probability Matrix:", probability_matrix)
    # print("Cost Matrix:", cost_matrix)

    simulation = DPSimulation(probability_matrix, cost_matrix)

    # cost_by_k = simulation.run(mode="k", K=1)
    cost_all = simulation.run(mode="all")

    print(cost_all)
    # print(cost_by_k, cost_all)
    # print(simulation.choice)  # Optimal actions from the latest run