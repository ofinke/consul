# Shortterm

- Probably migrate the ChatTurn to BaseMessage to unify it if I want to use langgraph ecosystem
- Go through the BaseAgentFlow and ReAct agent to unify it as much with ChatTask.


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