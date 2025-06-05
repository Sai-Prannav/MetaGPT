# MetaGPT Core Functional Logic Documentation

## 1. Introduction

This document details the core functional logic of MetaGPT, a multi-agent framework. It aims to explain the underlying architecture, key components, and their interactions to provide a clear understanding of how MetaGPT operates.

## 2. Core Architecture Overview

MetaGPT employs an event-driven, message-passing architecture. The system is built around three fundamental concepts:

*   **Roles (Agents):** These are specialized agents responsible for specific tasks or functions within the system. Each Role encapsulates its own logic and capabilities.
*   **Actions:** Actions define the specific operations or behaviors that a Role can perform. They are the building blocks of a Role's capabilities.
*   **Environment:** The Environment serves as the communication and operational backbone for the Roles. It manages the message flow between Roles and orchestrates their execution.

Roles interact by publishing messages to the Environment. The Environment then routes these messages to the appropriate Roles based on subscriptions and message addressing. This decoupled approach allows for flexible and scalable multi-agent workflows.

## 3. Key Components

### Roles (Agents)

The base `Role` class, defined in `metagpt/roles/role.py`, is the foundation for all specialized agents in MetaGPT.

*   **Primary Attributes:**
    *   `name` (str): A unique identifier for the Role.
    *   `profile` (str): Describes the Role's specialization (e.g., "Engineer", "ProductManager").
    *   `goal` (str): The overall objective the Role aims to achieve.
    *   `constraints` (str): Any limitations or rules the Role must adhere to.
    *   `actions` (list[Action]): A list of Action objects that the Role can perform.
    *   `rc` (RoleContext): An instance of `RoleContext` that holds the runtime data and context for the Role.

*   **The Observe-Think-Act Cycle:** This is the core operational loop for a Role.
    *   `_observe()`: The Role perceives its environment, primarily by checking for new messages in its `msg_buffer` (within `RoleContext`). It identifies relevant messages and potentially updates its internal memory.
    *   `_think()`: Based on the observed information and its current goal, the Role decides which action(s) to take next. This may involve selecting an action from its `actions` list or formulating a plan.
    *   `_act()`: The Role executes the chosen action(s). This typically involves calling the `run()` method of an `Action` object, which may result in new messages being published to the Environment.

*   **`react_mode`:** This attribute defines how a Role processes incoming messages and decides on actions.
    *   `REACT`: The Role processes all available messages in its buffer in one go, then thinks and acts. This is suitable for roles that need a comprehensive understanding of recent events before acting.
    *   `BY_ORDER`: The Role processes messages one by one, acting after each message. This is useful for sequential task processing.
    *   `PLAN_AND_ACT`: The Role first generates a plan (often a sequence of actions) based on its goal and observations, and then executes the plan. This is used for more complex, goal-oriented behavior.

#### `RoleContext`

Defined in `metagpt/utils/role_context.py` (Note: actual path might vary, common for context utilities). The `RoleContext` (`rc`) provides a dedicated runtime environment for each Role instance.

*   **Purpose:** To store and manage all runtime data specific to a Role, allowing Roles to be stateful and aware of their operational context.
*   **Key Attributes:**
    *   `env` (BaseEnv): A reference to the Environment in which the Role operates. This allows the Role to publish messages.
    *   `msg_buffer` (MessageQueue): A queue that stores incoming messages directed to the Role.
    *   `memory` (Memory): Stores long-term information and experiences of the Role.
    *   `state` (Field): A generic field to store the current state or status of the Role.
    *   `todo` (Action): Represents the next action the Role intends to perform.

### Actions

The base `Action` class, found in `metagpt/actions/action.py`, defines a discrete unit of work or capability that a Role can execute.

*   **Purpose:** To encapsulate a specific operation, such as calling an LLM, writing code, or analyzing data. Actions make Role behaviors modular and reusable.
*   **Key Attributes:**
    *   `name` (str): A descriptive name for the action.
    *   `i_context` (Any): Optional input context or data required by the action. This can be a Pydantic model for structured input.
    *   `prefix` (str): A system prompt or context string, often used when interacting with LLMs, to guide the LLM's behavior for this specific action. This is typically part of the `llm` configuration.

*   **The `run()` Method:** This is the main entry point for executing an Action. It contains the logic for the operation the Action performs. The `run()` method can be asynchronous (`async def run(...)`).
*   **Role of `ActionNode`:** `ActionNode` (from `metagpt/actions/action_node.py`) can be used to wrap actions and provide additional functionalities like creating hierarchies of actions (e.g., a parent action that calls multiple sub-actions). They are used in `metagpt/actions/add_requirement.py` and other system design actions.

### Messages

Messages, defined in `metagpt/schema.py` (typically as a Pydantic model, e.g., `Message`), are the central data structures for communication and data exchange between Roles within the Environment.

*   **Purpose:** To enable asynchronous communication and information flow, allowing Roles to trigger behaviors in other Roles or share data.
*   **Key Attributes:**
    *   `id` (str): A unique identifier for the message (e.g., a UUID).
    *   `content` (str): The primary payload of the message, usually a text string.
    *   `instruct_content` (Optional[PydanticBaseModel]): A field to carry structured data, often a Pydantic model. This allows for complex information to be passed reliably between actions and roles.
    *   `role` (str): The profile/role of the sender (e.g., "ProductManager", "User").
    *   `cause_by` (Type[Action]): The class of the Action that generated this message. This helps in tracing message origins and understanding context.
    *   `sent_from` (str or Address): The specific Role or entity that sent the message.
    *   `send_to` (str or Address or Set[Address]): The intended recipient(s) of the message. Can be a specific Role name, a Role type, or a set of addresses.

*   **How `instruct_content` allows passing Pydantic models:** By defining `instruct_content` as a Pydantic model type (or `Any` and then checking the type), Roles can send and receive complex, validated data structures. For example, an `Engineer` role might receive a `Message` where `instruct_content` is an instance of `CodingContext`, providing detailed instructions for code generation. This promotes clear and robust inter-role communication.

### Environment

The `BaseEnv` class (and its typical implementation `Environment`), defined in `metagpt/environment/base_env.py`, acts as the central hub for Role interaction and message dispatch.

*   **Purpose:** To manage a collection of Roles and facilitate communication between them. It decouples Roles from each other, as they only interact with the Environment.
*   **Manages a collection of Roles:**
    *   The `add_role(role: Role)` method allows adding Roles to the Environment.
    *   The `roles` attribute (often a dictionary) stores the registered Roles.

*   **`publish_message(message: Message)`:** This is the core mechanism for message dissemination.
    *   When a Role calls `env.publish_message(msg)`, the Environment iterates through all its managed Roles.
    *   It checks if a Role is subscribed to the message. Subscription can be implicit (a Role generally receives messages addressed to its `name` or `profile`) or explicit.
    *   The `send_to` field of the `Message` object is primarily used for routing. If `send_to` specifies a Role name, only that Role receives it. If it specifies a profile, all Roles with that profile might receive it.
    *   The `member_addrs` attribute of a Role (derived from its `name` and `profile`) is used by the Environment to match against the `send_to` field of the message.
    *   If a Role is deemed a recipient, the message is added to that Role's `msg_buffer`.

*   **`history`:** The Environment often maintains a `history` (e.g., `self.history: list[Message]`) which is a chronological log of all messages published within it. This is useful for debugging, auditing, and providing context to Roles.

*   **The `run()` method:** This method typically orchestrates the overall execution flow.
    *   It may involve initializing Roles.
    *   It often enters a loop where it checks for active Roles (Roles with messages to process or tasks to do) and allows them to execute their observe-think-act cycles.
    *   The loop continues until a termination condition is met (e.g., no more messages, or a specific goal is achieved).

### Team

The `Team` class, defined in `metagpt/team.py`, represents a higher-level abstraction for managing a group of Roles and an Environment to achieve a common, complex goal, such as developing a software project.

*   **Purpose:** To simplify the setup and execution of multi-agent workflows by encapsulating the Environment and the associated Roles.
*   **Higher-level abstraction:** A `Team` typically initializes its own `Environment` and populates it with a predefined set of Roles (e.g., ProductManager, Architect, Engineer, QAEngineer).
*   **`run_project(idea: str)`:** This method is often the main entry point to start a workflow.
    *   It takes an initial idea or requirement (e.g., "Create a command-line snake game").
    *   It then typically creates an initial `Message` containing this idea.
    *   This initial message is published to the Team's Environment, usually directed at a specific starting Role (e.g., ProductManager), thereby kicking off the multi-agent collaboration process.

*   **The main `run()` loop:**
    *   The `Team`'s `run()` method (or a similar method like `_run_environment` or directly calling `environment.run()`) drives the execution.
    *   It effectively starts the Environment's `run()` loop, which in turn allows the Roles within that Environment to begin their observe-think-act cycles, processing messages and collaborating until the project goal is met or no further actions can be taken.

This initial structure provides a foundational understanding of MetaGPT's key components and their interactions. Further sections can delve into specific implementations, advanced features, and usage examples.

## 4. Agent Types and Differentiation

MetaGPT achieves specialized agent behaviors through distinct configurations of Roles, primarily their goals, profiles, assigned actions, and the types of messages they are programmed to watch for.

**Examples of Specific Agent Types:**

*   **`ProductManager` (from `metagpt/roles/product_manager.py`):**
    *   **Primary `goal`:** "To generate comprehensive and clear product requirements."
    *   **Primary `profile`:** "Product Manager"
    *   **Typical `Action` classes:** Initialized with actions like `WritePRD` (Write Product Requirement Document), `GenerateUserStories`.
    *   **`_watch`es for:** Typically starts the workflow by processing an initial idea/message (e.g., from `UserRequirement` or a simple `Message` with the project idea). May also watch for messages from `Architect` or `Engineer` requesting clarification or providing feedback on requirements (e.g., `cause_by=AskReview`).

*   **`Architect` (from `metagpt/roles/architect.py`):**
    *   **Primary `goal`:** "To design a robust and scalable system architecture."
    *   **Primary `profile`:** "Architect"
    *   **Typical `Action` classes:** `WriteDesign` (to create system design documents, API specifications), `AnalyzeRequirements`.
    *   **`_watch`es for:** Messages from `ProductManager` containing product requirements (e.g., `cause_by=WritePRD`). It needs the PRD to start designing.

*   **`Engineer` (from `metagpt/roles/engineer.py`):**
    *   **Primary `goal`:** "To develop high-quality code based on system design and task specifications."
    *   **Primary `profile`:** "Engineer"
    *   **Typical `Action` classes:** `WriteCode`, `FixBug`, `WriteCodeReviewComment`. It often has a set of specific coding-related actions.
    *   **`_watch`es for:** Messages from `Architect` containing design documents and task breakdowns (e.g., `cause_by=WriteDesign`). It might also watch for messages from `QAEngineer` reporting bugs (e.g., `cause_by=ReportBug`).

*   **`QAEngineer` (from `metagpt/roles/qa_engineer.py`):**
    *   **Primary `goal`:** "To ensure the quality of the software through rigorous testing."
    *   **Primary `profile`:** "QA Engineer"
    *   **Typical `Action` classes:** `WriteTest`, `ReportBug`, `RunTests`.
    *   **`_watch`es for:** Messages from `Engineer` indicating code completion for a feature or task (e.g., `cause_by=WriteCode`). It needs the codebase or a notification that code is ready for testing.

**How Differentiation Leads to Specialized Behavior:**

The combination of a Role's `goal`, `profile`, specific `actions`, and its `watch` list (defined in `self.rc.watch` which is typically populated based on `set_actions()` or `_init_actions()`) dictates its specialization.
*   `goal` and `profile` guide the LLM's behavior when the Role `_thinks` to decide on the next action.
*   The specific `Action` classes provide the tools to achieve its goal. An `Engineer` has `WriteCode`, while a `ProductManager` has `WritePRD`.
*   The `_watch` list ensures a Role only reacts to relevant events. An `Engineer` doesn't act on a new user story until the `Architect` has translated it into a design specification. This creates a dependency chain and structured workflow.

**Inheritance and Base Classes (e.g., `RoleZero`):**

Some Roles might inherit from intermediate base classes like `RoleZero` (if present, e.g., in `metagpt/roles/role_zero.py`). Such base classes can provide:
*   **Shared Initialization Logic:** Common setup for certain types of roles (e.g., roles that primarily interact with LLMs for generation tasks).
*   **Predefined `react_mode` or other configurations:** Setting defaults that are common for a subset of roles.
*   **Utility methods:** Helper functions that are useful across several related roles.
For example, `RoleZero` might provide a more streamlined `_think` process or common utility for handling LLM responses, which is then inherited by more specialized roles like `ProductManager` or `Architect`, allowing them to focus on their specific prompt engineering and action definitions rather than boilerplate code. This contributes to differentiation by allowing specialized roles to build upon a common foundation, reducing redundancy and enforcing consistency where needed.

## 5. Inter-Agent Communication Mechanisms

The entire workflow in MetaGPT is driven by messages. Understanding how they are constructed, published, routed, and received is key.

**Message Construction:**

After a Role completes an action in its `_act()` phase (e.g., `WritePRD().run()`), it typically constructs a `Message` object.
*   `content`: Contains the main output of the action (e.g., the PRD text, the generated code, or a summary).
*   `instruct_content`: If the output is structured data (e.g., a list of tasks, API endpoints), it's placed here, often as a Pydantic model instance (e.g., `DesignContent`, `CompletedTasks`).
*   `cause_by`: Set to the class of the `Action` that just ran (e.g., `WritePRD`). This is crucial for routing and context.
*   `sent_from`: Set to the current Role's identity (e.g., `self.profile` or `self.name`).
*   `send_to`: Specifies the intended recipient(s). This can be:
    *   A specific Role name (e.g., "Architect").
    *   A Role profile (e.g., "Engineer"), in which case all Engineers might receive it.
    *   Left empty or set to a broadcast address if the message is for general consumption by any interested Role.

**Message Publishing:**

The Role then publishes this message to the environment:
```python
# Inside a Role's _act() method, after an action_output
new_message = Message(content=action_output_string,
                      instruct_content=structured_data, # optional
                      cause_by=type(self.rc.todo), # the action just performed
                      sent_from=self.profile,
                      send_to="Architect") # Example: sending to Architect
self.publish_message(new_message)
```
`self.publish_message(msg)` is a helper method in `Role` that calls `self.rc.env.publish_message(msg)`.

**Environment Routing (`Environment.publish_message`):**

1.  When `Environment.publish_message(message)` is called:
2.  The Environment adds the message to its global `history`.
3.  It iterates through all Roles registered in `self.roles.values()`.
4.  For each `role` in the environment, it checks if this role should receive the message. This is typically done by comparing the `message.send_to` field with the role's own addresses (name and profile). A common helper might be:
    ```python
    # Simplified logic, actual implementation might vary
    # role.addresses would be a set like {role.name, role.profile}
    # message.send_to could be a string or a set of strings

    def is_send_to(message_send_to, role_addresses):
        if not message_send_to: # Broadcast or general message
            return True
        if isinstance(message_send_to, str):
            return message_send_to in role_addresses
        if isinstance(message_send_to, set):
            return bool(message_send_to.intersection(role_addresses))
        return False

    # Inside Environment.publish_message loop:
    # if is_send_to(message.send_to, role.addresses):
    #    role.put_message(message)
    ```
5.  If a Role is identified as a recipient (i.e., `is_send_to` returns `True`), the Environment calls `role.put_message(message)`. This method adds the `message` to the Role's internal `msg_buffer` (a `MessageQueue`).

**Message Reception (`Role._observe`):**

1.  During its `_observe()` phase, a Role checks its `self.rc.msg_buffer`.
2.  It retrieves messages one by one (or in a batch, depending on `react_mode`).
3.  For each retrieved `message`, the Role filters it:
    *   **`cause_by` filtering:** The `message.cause_by` (the type of Action that created the message) must be in `self.rc.watch`. `self.rc.watch` is a set of Action types the Role is interested in. This ensures the Role only processes messages resulting from actions it cares about.
        ```python
        # Simplified logic in _observe or a helper method
        # if type(message.cause_by) not in self.rc.watch:
        #     return # Ignore message
        ```
    *   **`send_to` filtering (double check):** Although the Environment routes, the Role might perform an additional check to ensure the message was indeed intended for it, especially if messages can be "peeked" or if routing is complex.
    *   **Memory filtering:** If `self.config.enable_memory` is true, the Role checks if the message's ID is already in `self.rc.memory` to avoid processing duplicates.
        ```python
        # if self.config.enable_memory and message.id in self.rc.memory.get_message_ids():
        #    return # Ignore, already processed
        ```
4.  If a message passes all filters, it's considered "news."
5.  The `message` (or its relevant parts) is added to `self.rc.news` (a temporary list for the current observation cycle).
6.  The `message` is then typically added to `self.rc.memory.add(message)` to record that it has been seen and processed.

**Example Workflow Snippet: `Engineer` to `QAEngineer`**

1.  **Engineer's `_act()`:**
    *   The `Engineer` Role runs its `WriteCode` action.
    *   `WriteCode` finishes, producing source code.
    *   The `Engineer` constructs a `Message`:
        *   `content`: "Implemented feature X, code is in file_path.py."
        *   `instruct_content`: Potentially a `CodingContext` object with details of the commit, file paths, etc.
        *   `cause_by`: `WriteCode` (the class itself, not an instance).
        *   `sent_from`: "Engineer" (or specific engineer name).
        *   `send_to`: "QAEngineer" (profile) or a specific QA Engineer's name.
    *   `Engineer` calls `self.publish_message(new_code_message)`.

2.  **Environment Routing:**
    *   The `Environment` receives `new_code_message`.
    *   It iterates through its Roles. When it encounters a `QAEngineer` Role:
        *   It checks if "QAEngineer" is in `new_code_message.send_to`. It is.
        *   The `Environment` calls `qa_engineer_role.put_message(new_code_message)`.

3.  **QAEngineer's `_observe()`:**
    *   The `QAEngineer`'s `msg_buffer` now contains `new_code_message`.
    *   During `_observe()`, it retrieves this message.
    *   It checks `new_code_message.cause_by` (which is `WriteCode`). Let's assume `WriteCode` is in `qa_engineer_role.rc.watch`.
    *   The message passes filters and is added to `self.rc.news` and `self.rc.memory`.

4.  **QAEngineer's `_think()` and `_act()`:**
    *   In `_think()`, seeing the `WriteCode` message, the `QAEngineer` decides its `todo` should be `WriteTest` (or `RunTests` if tests already exist).
    *   In `_act()`, it runs the `WriteTest` action, using the information from the `new_code_message` (e.g., file paths) to generate and execute tests.

## 6. Key Smaller Components & Concepts

Several other components and concepts are vital for the detailed functioning of MetaGPT.

**Memory (`metagpt/memory/memory.py`, `metagpt/memory/longterm_memory.py`):**

*   **`Memory` (`self.rc.memory`):** Each Role instance has a `Memory` object (often just called `Memory` or `ShortTermMemory` in practice) within its `RoleContext` (`self.rc.memory`).
    *   **How it's used:** Its primary function is to store a history of messages the Role has observed and processed. When `_observe()` processes messages from `msg_buffer`, it adds them to this memory using `self.rc.memory.add(message)`.
    *   This helps in:
        *   Avoiding reprocessing of the same message if `enable_memory` is on.
        *   Providing context for the `_think()` phase. The Role can access `self.rc.memory.get()` or similar methods to retrieve past messages, which can inform its decision-making process, especially for LLM-based thinking.
*   **`BrainMemory` / `LongTermMemory`:**
    *   While the basic `self.rc.memory` stores session-specific messages, `LongTermMemory` (if implemented and used, path might be `metagpt/memory/longterm_memory.py`) would aim to provide persistence of knowledge across different sessions or projects.
    *   **Potential Purpose:** It might store generalized learnings, successful solutions to past problems, or user feedback that can be recalled by agents in future tasks to improve performance or adapt behavior. This is more akin to a knowledge base. Integration typically involves specific actions to query or update this memory.

**`RoleContext.state` and `Role._think()` for State Management:**

*   **`RoleContext.state`:** This attribute (e.g., `self.rc.state: int = 0`) allows a Role to maintain an internal state, often representing its current stage in a multi-step process or workflow.
*   **`Role._think()` for State Management:**
    *   The `_think()` method is crucial for managing this state. When a Role has multiple actions it can perform sequentially or based on conditions, `_think()` decides which action is next.
    *   If an LLM is used in `_think()` (common for more complex roles), the current `self.rc.state`, along with recent messages and the overall goal, can be part of the prompt to the LLM.
    *   The LLM's response can then suggest the next action or the next state. The `_think()` method would parse this response and update `self.rc.todo` (the next action to perform) and `self.rc.state` accordingly.
    *   For example, an `Engineer` might have states like "awaiting_design", "coding", "testing_pending", "fixing_bug". The `_think()` method transitions between these based on incoming messages and the results of its actions.

**`instruct_content` and Pydantic Models (`metagpt/schema.py`):**

*   **Reiterated Importance:** As mentioned before, `Message.instruct_content` is vital for robustly passing structured data. Instead of just plain text in `Message.content`, `instruct_content` can carry an instance of a Pydantic model.
*   **Examples:**
    *   `CodingContext`: May contain file names, code snippets, dependencies, and task descriptions for an `Engineer`.
    *   `DesignContext`: May contain diagrams, API endpoints, data schemas for an `Architect` or `Engineer`.
    *   `TestResultContext`: May contain pass/fail statuses, logs, and error messages for a `QAEngineer`.
*   **Type-Safe Data Exchange:** Pydantic models ensure that the data being passed is validated against a defined schema. The sending Role constructs the model, and the receiving Role can access its attributes with type safety, reducing errors from malformed or unexpected data. This makes inter-role communication more reliable and easier to debug.

**`ProjectRepo` (`metagpt/utils/project_repo.py`) and File Management:**

*   **Role:** `ProjectRepo` (or a similar utility like `FileRepository`) provides a centralized way to manage the file system artifacts generated during a project (e.g., software development).
    *   It typically abstracts file paths, making it easier to organize and access project files like source code, design documents, test scripts, requirement documents, etc.
    *   It might offer methods like `save(filename, content)`, `read(filename)`, `get_path(artefact_type)`.
*   **How Roles Use It:**
    *   An `Engineer`'s `WriteCode` action would use `ProjectRepo.save("src/module/file.py", generated_code)`.
    *   An `Architect`'s `WriteDesign` action would save its output using `ProjectRepo.save("docs/system_design.md", design_document_text)`.
    *   A `QAEngineer` might use it to read code files for analysis or to write test result logs.
    *   This ensures all project files are stored in a consistent and predictable location.

**`Planner` (`metagpt/strategy/planner.py`):**

*   **Role:** The `Planner` is primarily used when a Role is configured with `react_mode = PLAN_AND_ACT`.
*   **How it Works:**
    *   When such a Role receives a high-level goal or message, its `_think()` phase might invoke the `Planner`.
    *   The `Planner` takes the goal and, often using an LLM, breaks it down into a sequence of `Task` objects. Each `Task` might correspond to one of the Role's available `Action`s or a sub-goal.
    *   The `Planner` might store this sequence of tasks (the plan) within the Role's context (e.g., in `self.rc.plan`).
    *   The Role then executes these tasks/actions sequentially. After each action, it might re-evaluate the plan (e.g., mark task as complete, handle failures, or even re-plan if necessary).
    *   This allows for more sophisticated, multi-step reasoning and execution compared to a purely reactive approach.

**Configuration (`metagpt/config2.py`, `metagpt/configs/`):**

*   **How the System is Configured:** MetaGPT relies on a configuration system to manage settings like:
    *   LLM provider details (e.g., OpenAI API key, model name like `gpt-4`, `gpt-3.5-turbo`).
    *   Project paths (e.g., the root directory for `ProjectRepo`).
    *   Debugging flags.
    *   Specific Action-level configurations (e.g., prompts, parameters).
*   **Location:**
    *   `metagpt/config2.py` (or `config.py`) often defines the main configuration class (e.g., `Config` or `MetaGPTConfig`) and how settings are loaded (e.g., from environment variables, YAML files).
    *   The `metagpt/configs/` directory might contain default configuration files (e.g., `config.yaml.example`) or specific profiles.
    *   Users can typically override default configurations by providing their own YAML file or setting environment variables. This allows for flexibility in adapting MetaGPT to different LLMs or operational environments.

This concludes the detailed sections. These should provide a comprehensive understanding of MetaGPT's inner workings.

## Documentation Clarity and Accuracy Tests

This section provides a series of questions to test the clarity and accuracy of the documentation. If these questions can be answered thoroughly and correctly using the information presented in this document, it indicates a good level of detail and understanding.

1.  **Role Initialization:** How is a `Role` object initialized with its specific `goal`, `profile`, and initial set of `Action` objects?
2.  **Action Execution:** Describe the process that occurs when a `Role` decides to execute a specific `Action`. What methods are involved in the `Role` and `Action` classes?
3.  **Message Creation:** When an `Action` completes, how is a `Message` object typically constructed? What are the essential fields that need to be populated (e.g., `cause_by`, `sent_from`, `send_to`, `content`, `instruct_content`)?
4.  **Message Routing:** Explain the step-by-step process of how a `Message` published by one `Role` reaches the `msg_buffer` of a recipient `Role`. What role does the `Environment` play in this?
5.  **Message Filtering:** When a `Role`'s `_observe()` method is called, what criteria are used to filter messages from its `msg_buffer` before they are processed?
6.  **State Management:** How does a `Role` with multiple actions determine which action to perform next? Explain the role of `RoleContext.state` and the `_think()` method.
7.  **Structured Data Transfer:** How does `Message.instruct_content` facilitate the transfer of complex, structured data between `Role`s? Provide an example using a context model like `CodingContext`.
8.  **Agent Differentiation:** What are the primary mechanisms or attributes within the `Role` class and its derived classes that allow for the creation of specialized agents like `Architect` and `Engineer`?
9.  **Team Orchestration:** How does the `Team` class initiate and manage a project workflow involving multiple `Role`s? What is the entry point for starting a task?
10. **Environment's Role in Communication:** What specific data structure within the `Environment` is critical for ensuring messages are delivered to the correct `Role`s based on their subscriptions? (Hint: See section 3, Environment, `publish_message` and attribute `member_addrs` of a Role).

## Documentation Completeness Checklist

This checklist helps ensure that all critical functional aspects of MetaGPT's core logic have been covered in the documentation.

*   [ ] **Core Architecture:** Is the overall event-driven, message-passing architecture clearly explained?
*   [ ] **Role Class (`Role`):**
    *   [ ] Initialization (profile, goal, actions)
    *   [ ] Observe-Think-Act cycle (`_observe`, `_think`, `_act`)
    *   [ ] `RoleContext` and its attributes (`env`, `msg_buffer`, `memory`, `state`, `todo`)
    *   [ ] `react_mode` options
    *   [ ] Memory management (`self.rc.memory`)
*   [ ] **Action Class (`Action`):**
    *   [ ] Initialization and purpose
    *   [ ] `run()` method
    *   [ ] `i_context` (input context)
    *   [ ] Role of `ActionNode`
*   [ ] **Message Schema (`Message`):**
    *   [ ] Key attributes (`id`, `content`, `instruct_content`, `role`, `cause_by`, `sent_from`, `send_to`)
    *   [ ] Use of `instruct_content` for Pydantic models
*   [ ] **Environment Class (`Environment`):**
    *   [ ] Role management (adding roles)
    *   [ ] `publish_message()` mechanism and message routing
    *   [ ] `member_addrs` structure (or how roles' addresses are used for routing)
    *   [ ] `history` logging
    *   [ ] `run()` method for orchestrating role execution
*   [ ] **Team Class (`Team`):**
    *   [ ] Relationship with Environment
    *   [ ] `run_project()` and `run()` methods
    *   [ ] Initiation of workflow via an initial message
*   [ ] **Agent Types and Differentiation:**
    *   [ ] Examples of specific agent types (e.g., `Architect`, `Engineer`)
    *   [ ] Explanation of how their configurations (actions, watched messages) create specialization
*   [ ] **Inter-Agent Communication:**
    *   [ ] Message construction process
    *   [ ] Publishing via `Role.publish_message`
    *   [ ] Routing via `Environment.publish_message`
    *   [ ] Reception and filtering via `Role._observe`
    *   [ ] Example workflow trace
*   [ ] **Key Smaller Components:**
    *   [ ] `Memory` objects (`self.rc.memory`)
    *   [ ] `ProjectRepo` for file management
    *   [ ] `Planner` and `Task` objects (for `PLAN_AND_ACT` mode)
    *   [ ] Configuration system overview (`config2.py`)
