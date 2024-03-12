# Add imports
from minject import Registry, inject

# Initialize a Registry
registry = Registry()


# Create classes with dependency hierarchy specified
# through the inject.bind function.
@inject.bind(message_start="I was initialized", message_end="with dependency injection")
class DependencyOne:
    def __init__(self, message_start: str, message_end: str):
        self.message_start = message_start
        self.message_end = message_end


@inject.bind(greeting="Bonjour")
class DependencyTwo:
    def __init__(self, greeting: str):
        self.greeting = greeting


@inject.bind(dep1=inject.reference(DependencyOne), dep2=inject.reference(DependencyTwo))
class MessageBuilder:
    def __init__(self, dep1: DependencyOne, dep2: DependencyTwo):
        self.dep1 = dep1
        self.dep2 = dep2

    def get_message(self):
        return f"{self.dep2.greeting}! {self.dep1.message_start} {self.dep1.message_end}."


# Instantiate a class through the registry
message_builder = registry[MessageBuilder]

# Use the class
message = message_builder.get_message()
print(message)

assert message == "Bonjour! I was initialized with dependency injection."
# You should see this string as the output of your script
