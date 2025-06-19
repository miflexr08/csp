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

    def get_arcs(self):
        arcs = list()
        for x in self.crossword.variables:
            for y in self.crossword.variables:
                if self.crossword.overlaps.__contains__((x, y)):
                    arcs.append((x, y))
        return arcs

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
        remove_actions = []
        if intersection:
            for word_x in self.domains[x]: # words for Variable 'x'
                for word_y in self.domains[y]: # words for Variable 'y'
                    if word_x[x_overlapping_char_index] != word_y[y_overlapping_char_index]:
                        remove_action = lambda: self.domains[x].remove(word_x)
                        remove_actions.append(remove_action)
                        if not revised:
                            revised = True
        if revised:
            for remove in remove_actions:
                remove()

        return revised

        #words_to_remove = set()
        #if intersection:
            #for word_x in self.domains[x]:
                #for word_y in self.domains[y]:
                    #if word_x[x_overlapping_char_index] != word_y[y_overlapping_char_index]:
                        #words_to_remove.add(word_x)
                        #if not revised:
                            #revised = True

        #if revised:
            #self.domains[x] -= words_to_remove  # usando diferença de conjuntos

    def ac3(self, arcs=None):

        # First call
        if arcs is None:
            arcs = self.get_arcs()

        consistent = True
        for arc in arcs:
            if self.revise(arc[0], arc[1]):
                if not self.domains[arc[1]]:
                    consistent = False

        return consistent

    def assignment_complete(self, assignment):
        return len(assignment) == len(self.crossword.variables)

    def consistent(self, assignment: dict):
        return len(assignment.values()) == len(set(assignment.values()))

    def select_unassigned_variable(self, assignment: dict):
        unassigned_vars = list()
        assignment_keys = assignment.keys()
        for var in self.crossword.variables:
            if not assignment_keys.__contains__(var):
                unassigned_vars.append(var)

        less_remaining = len(self.crossword.words)
        selected_vars = []
        for var in unassigned_vars:
            if len(self.domains[var]) <= less_remaining:
                less_remaining = len(self.domains[var])
                selected_vars.append(var)

        if len(selected_vars) > 1:

            selected_var = None
            max_neighboors = 0
            for var in selected_vars:
                neighboors = self.crossword.neighbors(var)
                neighboors_qt = len(neighboors)
                if neighboors_qt >= max_neighboors:
                    selected_var = var
                    max_neighboors = neighboors_qt

            return selected_var

        elif len(selected_vars):
            return selected_vars[0]

    def backtrack(self, assignment: dict):

        variable = self.select_unassigned_variable(assignment)
        neighboors = self.crossword.neighbors(variable)

        order_domain_values = self.order_domain_values(variable, assignment)
        domain_current_state = self.domains.copy()  # Not Sure If It is Necessary to Copy Complete Domain
        if len(order_domain_values):
            word = order_domain_values[0]  # Make Tests with and without ordering
            self.domains[variable] = [word]
            assignment[variable] = word

            # Insert In the get_arcs Function (?)
            arcs = list()
            for n in neighboors:
                arcs.append((variable, n))

            arc_consistent = self.ac3(arcs)
            if arc_consistent:
                if self.assignment_complete(assignment):
                    # base case #B
                    return assignment
            else:  # A Atribuição Não Deu Certo na Stack Frame Atual
                # self.domains = domain_current_state
                self.domains[variable] = domain_current_state[variable] - word
                del assignment[variable]
        else:
            return None

        result = self.backtrack(assignment)  # Uma Atribuição Numa Stack Frame Acima Não Deu Certo
        # 1.1 - We just come here when backtrack finally returns something
        # 1.2 - We always go "back" to the top of the function (remember that)
        if result is None:  # Restaurar Estado e Seguir Adiante
            self.domains = domain_current_state
            # self.domains[variable] = domain_current_state[variable] - word # Is That Right?
            del assignment[variable]

            return self.backtrack(assignment)

        return result

    def order_domain_values(self, var, assignment: dict):
        """
        Return a list of values in the domain of `var`, in order by
        the number of values they rule out for neighboring variables.
        The first value in the list, for example, should be the one
        that rules out the fewest values among the neighbors of `var`.
        """
        return self.domains[var]



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


