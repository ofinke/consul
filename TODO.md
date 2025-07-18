# Shortterm

- Fix history in the CLI interface to also contains TOOL messages
  - I'm taking only the last AI message as the answer, but I would like to keep the tool messages too
- Add conversation saving to markdown
- Redo tools as MCP
- Various TODOs accross the app

# Next steps

- merge to dev
- Implement agent for tests
  - Tools: open file, create a new file
  - Goal: User describes what wants to document and the agent tries to create a new md file with the description
- Implement agent for docs
  - Tools: open file, create a new file
  - Goal: Agent creates a set of tests into a new file
  - Future idea: it can trigger the tests and see the results and use them to modify existing tests.
- Implement agent for explaining code