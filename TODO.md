# Shortterm

- Unification of text outputs into terminal using TerminalHandler
  - Separate markdown styler and smart text wrap so I can select which one is called. Or keep it and add markdown formatting as a flad?
  - What and how I can handle message formatting and emitting from CLI interface? I'm now mainly interested in colors of You, Assistant and Command
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