from collections import OrderedDict
import os


class CmdlineParser(object):
    def __init__(self):
        self.template = []
        self.configuration = OrderedDict()
        self._preparsed = False

    def format(self, configuration):
        return " ".join(self.template).format(**configuration)

    def parse(self, commandline):
        if not commandline:
            return {}

        parsed_commandline = []
        for arg in commandline:
            if "=" in arg:
                parsed_commandline += arg.split("=")
            else:
                parsed_commandline.append(arg)

        positional_index = 0
        argument_name = None
        # todo: resort alphabetically to that reordering of commandline fits to same trial.
        self.configuration = OrderedDict()
        for arg in parsed_commandline:
            # Key
            if os.path.exists(arg):
                arg = os.path.abspath(arg)

            if arg.startswith("-"):
                argument_name = arg.lstrip("-")
                self.configuration[argument_name] = []
                if arg not in self.template:
                    self.template.append(arg)
            # Optional
            elif argument_name is not None:
                pos = len(self.configuration[argument_name])
                item_template = ("{" + argument_name + "}")
                prev_template = "{" + argument_name + "[" + str(pos - 1) + "]}"
                template = "{" + argument_name + "[" + str(pos) + "]}"
                # Add new position
                if pos == 0 and item_template in self.template:
                    self.template[self.template.index(item_template)] = template
                elif pos > 0 and prev_template in self.template:
                    self.template.insert(self.template.index(prev_template), template)
                else:
                    self.template.append(template)

                self.configuration[argument_name].append(arg)
            # TODO: Support passing the same commandline but slightly different
            elif self._preparsed:
                raise RuntimeError("Cannot branch using positional arguments.")
            # Positional
            else:
                key = "_pos_{}".format(positional_index)
                self.configuration[key] = arg
                positional_index += 1
                self.template.append("{" + key + "}")

        for key, value in list(self.configuration.items()):
            if isinstance(value, list) and len(value) == 0:
                self.configuration[key] = True

            if isinstance(value, list) and len(value) == 1:
                self.configuration[key] = value[0]
                template = "{" + key + "[0]}"
                self.template[self.template.index(template)] = "{" + key + "}"

        self._preparsed = True

        return self.configuration
