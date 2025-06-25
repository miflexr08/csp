import sys

from crossword import *

class CrosswordCreator():

    def __init__(self, crossword: Crossword):
        self.crossword = crossword
        self.domains = {
            var: self.crossword.words.copy()
            for var in self.crossword.variables
        }
        self.arcs = list()

    def letter_grid(self, assignment):
        letters = [
            [None for _ in range(self.crossword.width)]
            for _ in range(self.crossword.height)
        ]
        for variable, word in assignment.items():
            direction = variable.direction
            for k in range(len(word)):
                i = variable.i + (k if direction == Variable.DOWN else 0)
                j = variable.j + (k if direction == Variable.ACROSS else 0)
                letters[i][j] = word[k]
        return letters

    def print(self, assignment):
        letters = self.letter_grid(assignment)
        for i in range(self.crossword.height):
            for j in range(self.crossword.width):
                if self.crossword.structure[i][j]:
                    print(letters[i][j] or " ", end="")
                else:
                    print("█", end="")
            print()

    def save(self, assignment, filename):
        from PIL import Image, ImageDraw, ImageFont
        cell_size = 100
        cell_border = 2
        interior_size = cell_size - 2 * cell_border
        letters = self.letter_grid(assignment)

        # Create a blank canvas
        img = Image.new(
            "RGBA",
            (self.crossword.width * cell_size,
             self.crossword.height * cell_size),
            "black"
        )
        font = ImageFont.truetype("assets/fonts/OpenSans-Regular.ttf", 80)
        draw = ImageDraw.Draw(img)

        for i in range(self.crossword.height):
            for j in range(self.crossword.width):

                rect = [
                    (j * cell_size + cell_border,
                     i * cell_size + cell_border),
                    ((j + 1) * cell_size - cell_border,
                     (i + 1) * cell_size - cell_border)
                ]
                if self.crossword.structure[i][j]:
                    draw.rectangle(rect, fill="white")
                    if letters[i][j]:
                        _, _, w, h = draw.textbbox((0, 0), letters[i][j], font=font)
                        draw.text(
                            (rect[0][0] + ((interior_size - w) / 2),
                             rect[0][1] + ((interior_size - h) / 2) - 10),
                            letters[i][j], fill="black", font=font
                        )

        img.save(filename)

    def solve(self):

        self.enforce_node_consistency()
        self.ac3()
        return self.backtrack(dict())

    def enforce_node_consistency(self):
        for var in self.crossword.variables:
            words = self.domains[var]

            filtered_words: set[str] = set()
            for w in words:
                if len(w) == var.length:
                    filtered_words.add(w)

            self.domains[var] = filtered_words

    def revise(self, x: Variable, y: Variable):

        # Check for overlapping characters between variables (edges in constraint graph):
        # Returns (i, j) where:
        #   i: index of the overlapping character in the first variable
        #   j: index of the overlapping character in the second variable
        overlap: tuple = self.crossword.overlaps.get((x, y))

        # Técnica aprendida 1. descontrução de tupla
        x_overlap_idx, y_overlap_idx = overlap

        revised = False
        words_to_remove = []
        for word_x in self.domains[x]:

            # Técnica aprendida 2: método any
            # Verificar se existe pelo menos uma palavra em y que satisfaça a restrição
            if not any(word_x[x_overlap_idx] == word_y[y_overlap_idx] for word_y in self.domains[y]):
                words_to_remove.append(word_x)

            # inconsistent_x = True
            # for word_y in self.domains[y]:
            #     if word_x[x_overlap_idx] == word_y[y_overlap_idx]:
            #         inconsistent_x = False
            # if inconsistent_x:
            #     words_to_remove.append(word_x)

        if words_to_remove:
            revised = True
            for w in words_to_remove:
                self.domains[x].remove(w)

        return revised

    def ac3(self, arcs: list[tuple[Variable, Variable]]=None):

        # First call
        if arcs is None:
            arcs = self.get_arcs()

        revised_vars = set()
        for arc in arcs:
            if self.revise(arc[0], arc[1]):
                revised_vars.add(arc[0])

        arcs = []
        for var in revised_vars:
            for n in self.crossword.neighbors(var):
                arcs.append((n, var))

        if len(arcs):
            self.ac3(arcs)

    def get_arcs(self) -> list[tuple[Variable, Variable]]:
        arcs = list()
        for x in self.crossword.variables:
            for y in self.crossword.variables:
                intersection = self.crossword.overlaps.get((x, y))
                if intersection is not None:
                    arcs.append((x, y))

        return arcs

    def assignment_complete(self, assignment):
        return len(assignment) == len(self.crossword.variables)

    def consistent(self, assignment: dict[Variable, str]) -> bool:

        meet_unary_constraints = True
        meet_binary_constraints = True
        for variable_key_i, word_i in assignment.items():
            if meet_unary_constraints:
                meet_unary_constraints = len(word_i) == variable_key_i.length
            for variable_key_j, word_j in assignment.items():
                if variable_key_i == variable_key_j:
                    continue
                if meet_binary_constraints:
                    intersection = self.crossword.overlaps.get((variable_key_i, variable_key_j))
                    if intersection is not None:
                        meet_binary_constraints = word_i[intersection[0]] == word_j[intersection[1]]

            if not meet_unary_constraints and not meet_binary_constraints:
                break

        duplicated = len(assignment.values()) != len(set(assignment.values()))
        return (meet_unary_constraints
                and meet_binary_constraints
                    and not duplicated)

    def select_unassigned_variable(self, assignment: dict) -> Variable:

        # Aplicar heurística MRV (Minimum Remaining Values)
        min_domain_size = float('inf')
        mrv_candidates = []
        for var in self.crossword.variables:
            if var in assignment:
                continue

            var_domain_size = len(self.domains[var])
            if var_domain_size == min_domain_size:
                mrv_candidates.append(var)
            elif var_domain_size < min_domain_size:
                min_domain_size = var_domain_size
                mrv_candidates.insert(0, var)

        if len(mrv_candidates) == 1:
            return mrv_candidates[0]

        # Aplicar heurística de Degree para desempate (variável com mais vizinhos)
        return max(mrv_candidates, key=lambda var: len(self.crossword.neighbors(var)))

    def choose(self, assignment, variable, word):
        self.domains[variable] = [word]
        assignment[variable] = word

    def get_state_copy(self):
        return self.domains.copy()

    def backtrack(self, assignment: dict[Variable, str]):
        domain_cp = self.get_state_copy()
        variable = self.select_unassigned_variable(assignment)
        order_domain_values = self.order_domain_values(variable, assignment)
        if len(order_domain_values):
            word = order_domain_values[0]  # Make Tests with ordered and unordered structure
            self.choose(assignment, variable, word)

            self.ac3()
            has_consistency = self.consistent(assignment)
            if has_consistency and self.assignment_complete(assignment):
                    return assignment
            elif not has_consistency:
                self.domains[variable].remove(word)
                del assignment[variable]
        else:
            return None

        assignment_result = self.backtrack(assignment)
        if assignment_result is None:
            self.domains = domain_cp
            del assignment[variable]

            return self.backtrack(assignment)

        return assignment_result

    def order_domain_values(self, var, assignment: dict):
        counter = { w: 0 for w in self.domains[var] }
        neighbors = self.crossword.neighbors(var)
        for word in self.domains[var]:
            for n in neighbors:
                overlap = self.crossword.overlaps.get((var, n))
                x_overlap_idx, y_overlap_idx = overlap
                for word_n in self.domains[n]:
                    if word[x_overlap_idx] != word_n[y_overlap_idx]:
                        counter[word] += 1

        return sorted(counter, key=lambda k: counter[k])




def main():
    # Check usage
    if len(sys.argv) not in [3, 4]:
        sys.exit("Usage: python generate.py structure words [output]")

    # Parse command-line arguments
    structure = sys.argv[1]
    words = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) == 4 else None

    # Generate crossword
    crossword = Crossword(structure, words)
    creator = CrosswordCreator(crossword)
    assignment = creator.solve()

    # Print result
    if assignment is None:
        print("No solution.")
    else:
        creator.print(assignment)
        if output:
            creator.save(assignment, output)


if __name__ == "__main__":
    main()

