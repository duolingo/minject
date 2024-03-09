# Add imports
from minject import Registry, inject

registry = Registry()


@inject.bind(
    message="Hello friend!",
)
class BindExample:
    def __init__(self, message: str):
        self.message = message

    def print_message(self):
        print(self.message)
        return self.message


bind_example = registry[BindExample]
message = bind_example.print_message()
assert message == "Hello friend!"


class DefineExample:
    def __init__(self, greeting: str):
        self.greeting = greeting

    def print_greeting(self):
        print(self.greeting)
        return self.greeting


define_example_definition = inject.define(DefineExample, greeting="¡Hola amigo!")
define_example = registry[define_example_definition]
greeting = define_example.print_greeting()
assert greeting == "¡Hola amigo!"


@inject.bind(
    salutation="Bonjour mon ami!",
)
class SalutationPrinter:
    def __init__(self, salutation: str):
        self.salutation = salutation

    def print_salutation(self):
        print(self.salutation)
        return self.salutation


@inject.bind(printer=inject.reference(SalutationPrinter))
class ReferenceExample:
    def __init__(self, printer: SalutationPrinter):
        self.printer = printer

    def print_with_printer(self):
        printed_str = self.printer.print_salutation()
        return printed_str


reference_example = registry[ReferenceExample]
printed_str = reference_example.print_with_printer()
assert printed_str == "Bonjour mon ami!"


@inject.bind(note="Hallo, Freund!")
class ResolvedClass:
    def __init__(self, note: str):
        self.note = note


def scream_resolved(resolved: ResolvedClass):
    return f"{resolved.note.upper()}!!"


@inject.bind(
    computed_message=inject.function(scream_resolved, resolved=inject.reference(ResolvedClass))
)
class FunctionExample:
    def __init__(self, computed_message: str):
        self.computed_message = computed_message

    def print_message(self):
        print(self.computed_message)
        return self.computed_message


function_example = registry[FunctionExample]
computed_message = function_example.print_message()
assert computed_message == "HALLO, FREUND!!!"
