# Shortterm

- Prepare tools for docs / test agents
- Prepare custom prompt variables, options:
  - Variables into user messages handled on the CLI / API side?
  - Variables from config handled on the flow classes side?
  - All variables handled on the flow side, leading to more custom flows.

# Next steps

- Polish the CLI slightly / merge to dev
- Implement Base class for agents
  - Should contain loop, look how it is implemented in laggraph
- Implement basic tools for agents
  - Open and load file (only in the project folder)
  - Create a new file (only in the project folder)
- Implement agent for tests
  - Tools: open file, create a new file
  - Goal: User describes what wants to document and the agent tries to create a new md file with the description
- Implement agent for docs
  - Tools: open file, create a new file
  - Goal: Agent creates a set of tests into a new file
  - Future idea: it can trigger the tests and see the results and use them to modify existing tests.
- Implement agent for explaining code