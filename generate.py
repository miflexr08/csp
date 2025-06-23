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
        intersection: tuple = self.crossword.overlaps.get((x, y))

        x_overlapping_char_index = intersection[0]
        y_overlapping_char_index = intersection[1]
        revised = False

        consistent_x_values = set()
        for word_x in self.domains[x]:
            for word_y in self.domains[y]:
                if word_x[x_overlapping_char_index] == word_y[y_overlapping_char_index]:
                    consistent_x_values.add(word_x)

            if len(self.domains[x]) != len(consistent_x_values):
                self.domains[x] = consistent_x_values
                revised = True

        return revised

    def ac3(self, arcs: list[tuple[Variable, Variable]]=None):

        # First call
        if arcs is None:
            arcs = self.get_arcs()

        for arc in arcs:
            var_x = arc[0]
            var_y = arc[1]
            if self.revise(var_x, var_y):
                pass
                # if not len(self.domains[var_x]):
                #     consistent = False

    def get_arcs(self) -> list[tuple[Variable, Variable]]:
        # it is possible to build it with List Comprehension
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
                min_domain_size = var_domain_size
                mrv_candidates.append(var)
            elif var_domain_size < min_domain_size:
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

            #arcs = [(variable, n) for n in self.crossword.neighbors(variable)]

            self.ac3()
            has_consistency = self.consistent(assignment)
            if has_consistency and self.assignment_complete(assignment):
                    return assignment
            elif not has_consistency:
                self.domains[variable].remove(word)
                del assignment[variable]
        else:
            return None

        # The assignment attempt in a previous recursion level has failed
        # Note 1: We only reach this point when the recursive backtrack call returns a result
        # Note 2: The recursive nature of backtracking means execution will always return to
        #         the caller's context when a recursive call completes
        assignment_result = self.backtrack(assignment)

        # Restaurar Estado e Seguir Adiante
        if assignment_result is None:
            self.domains = domain_cp
            del assignment[variable]

            return self.backtrack(assignment)

        return assignment_result

    def order_domain_values(self, var, assignment: dict):
        """
        Return a list of values in the domain of `var`, in order by
        the number of values they rule out for neighboring variables.
        The first value in the list, for example, should be the one
        that rules out the fewest values among the neighbors of `var`.
        """
        return list(self.domains[var])



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

