## Asyncio Event Loop Error — RCA & Resolution

### Issue

While integrating the LangGraph async workflow with the Streamlit frontend, the application failed at runtime with the following error:

```text
RuntimeError: Cannot run the event loop while another loop is running
```

The error occurred when Streamlit attempted to consume the asynchronous token generator using `st.write_stream()`:

```python
ai_response = st.write_stream(
    stream_token_generator(workflow, user_input, CONFIG)
)
```

The application was initially structured as:

```python
async def app():
    ...
    
if __name__ == "__main__":
    asyncio.run(app())
```

### Root Cause Analysis (RCA)

The root cause was **nested/competing asyncio event-loop management** between the application's `asyncio.run()` and Streamlit's handling of asynchronous generators.

The application started an event loop explicitly using:

```python
asyncio.run(app())
```

Since `app()` itself was asynchronous, the entire Streamlit execution was running inside an asyncio event loop.

Inside `app()`, an asynchronous generator was then passed to:

```python
st.write_stream(stream_token_generator(...))
```

`stream_token_generator()` internally used LangGraph's asynchronous streaming API:

```python
async for chunk, metadata in workflow.astream(
    ...,
    stream_mode="messages",
):
```

`st.write_stream()` is capable of consuming asynchronous generators and managing the required execution internally. __Therefore, wrapping the entire Streamlit application in `asyncio.run()` resulted in two layers attempting to manage asynchronous execution.__

Conceptually, the problematic execution flow was:

```text
asyncio.run(app())
        │
        ▼
  Event Loop A
        │
        ▼
 st.write_stream()
        │
        ▼
Async generator / Streamlit async handling
        │
        ▼
Attempt to run another event loop
        │
        ▼
RuntimeError
"Cannot run the event loop while another loop is running"
```

The traceback showed the failure while Streamlit was executing the asynchronous generator:

```text
File "...streamlit_frontend.py", line 86, in <module>
    asyncio.run(app())

...

File "...streamlit_frontend.py", line 81, in app
    ai_response = st.write_stream(
        stream_token_generator(workflow, user_input, CONFIG)
    )

...

RuntimeError: Cannot run the event loop while another loop is running
```

### Solution Adopted

The Streamlit application was changed from an asynchronous entry point to a synchronous one.

#### Before

```python
async def app():
    ...
    
if __name__ == "__main__":
    asyncio.run(app())
```

#### After

```python
def app():
    ...
    
if __name__ == "__main__":
    app()
```

Individual asynchronous operations that needed to be executed from the synchronous Streamlit application were explicitly awaited using `asyncio.run()`:

```python
workflow, conn = asyncio.run(build_workflow())

stored_threads = asyncio.run(
    fetch_all_thread_ids(conn)
)

chat_history = asyncio.run(
    load_chat_history(
        workflow,
        st.session_state["thread_id"]
    )
)
```

However, the LangGraph streaming generator was **not** wrapped in another `asyncio.run()`:

```python
ai_response = st.write_stream(
    stream_token_generator(
        workflow,
        user_input,
        CONFIG
    )
)
```

This allows Streamlit's `st.write_stream()` to handle the asynchronous generator appropriately.

### Final Execution Model

The corrected architecture separates the synchronous Streamlit lifecycle from individual asynchronous operations:

```text
Streamlit Application
        │
        ▼
    app()                 ← synchronous
        │
        ├── asyncio.run(build_workflow())
        │
        ├── asyncio.run(fetch_all_thread_ids())
        │
        ├── asyncio.run(load_chat_history())
        │
        └── st.write_stream(async_generator)
                         │
                         ▼
                 LangGraph astream()
                         │
                         ▼
                  Token-by-token output
```

### Why This Works

The important distinction is that `asyncio.run()` is now used only for **individual asynchronous operations**, rather than wrapping the entire Streamlit application.

The asynchronous LangGraph streaming operation is handed directly to:

```python
st.write_stream()
```

instead of attempting to manually create another event-loop execution context.

This prevents the application from trying to start or run an asyncio event loop while another event loop is already active.

### Key Takeaway

> **Do not wrap the entire Streamlit application in `asyncio.run()` when Streamlit itself is responsible for consuming an asynchronous generator.**

For this application:

* Keep the Streamlit entry point **synchronous**.
* Use `asyncio.run()` for isolated async operations when required.
* Pass asynchronous generators directly to `st.write_stream()`.
* Avoid nesting `asyncio.run()` calls or manually running event loops inside Streamlit's execution context.

This resolved the `Cannot run the event loop while another loop is running` runtime error and allowed the LangGraph response stream to be rendered token-by-token in the Streamlit UI.

### What `asyncio.run()` do?
- When you run 
```python
asyncio.run(main())
```
    Python does:
    ```text
    Create event loop
        ↓
    Start event loop
        ↓
    Run main()
        ↓
    main() executes async tasks
        ↓
    main() finishes
        ↓
    Close event loop
    ```

#### We cannnot have nested event-loops
```python
async def outer():
    asyncio.run(main())
```
and then:
`asyncio.run(outer())`
    Because now:
    ```text
    asyncio.run(outer())
            │
            ▼
    Event Loop A
            │
            ▼
        outer()
            │
            ▼
    asyncio.run(main())
            │
            ▼
    ❌ Try to create/run
        Event Loop B
    ```
- The problem is that Event Loop A is already running. Python doesn't allow you to do this in the same thread:
    ```text
    Event Loop A
        │
        └── start Event Loop B
    ```
#### This is correct
```python
def main():
    asyncio.run(A())
    asyncio.run(B())
```
- Though it is sequential, asyncio.run() creates and manages an event loop for each call.
```text
main()  [synchronous]
  │
  ├── asyncio.run(A())
  │       │
  │       ├── Create Event Loop #1
  │       ├── Run A()
  │       └── Close Event Loop #1
  │
  └── asyncio.run(B())
          │
          ├── Create Event Loop #2
          ├── Run B()
          └── Close Event Loop #2
```
- If you want both to run concurrently:
```text
Event Loop
   │
   ├── A ────────────────┐
   │                     │
   └── B ────────────┐   │
                     │   │
                     ▼   ▼
                   finish
```
- The key is that asyncio.gather() does NOT create another event loop. That's the distinction.

### Not Correct or Possible on the Same thread
```python
async def main():
    asyncio.run(A())   # ❌
    asyncio.run(B())   # ❌
```
- Because it initialises atleast 2 event-loops at a same time main()-loop, A()-loop or B()-loop
- __NOT VALID__
```text
main()
  │
  └── asyncio.run(A())
          │
          ▼
      Event Loop #1
          │
          ▼
         A()
          │
          └── asyncio.run(B())
                    │
                    ▼
               Event Loop #2 ❌
```
- __VALID__
```python
def main():
    asyncio.run(A())


async def A():
    await B()


async def B():
    await C()


async def C():
    await asyncio.sleep(1)
```
- because there is only 1 event-loop being created
    ```text
    main()                         ← synchronous
    │
    │ asyncio.run(A())
    ▼
    ┌──────────────────────────────┐
    │ Event Loop                   │
    │                              │
    │   A()                        │
    │    │                         │
    │    │ await B()               │
    │    ▼                         │
    │   B()                        │
    │    │                         │
    │    │ await C()               │
    │    ▼                         │
    │   C()                        │
    │    │                         │
    │    └── await sleep()         │
    │                              │
    └──────────────────────────────┘
    ```

## Run the Streamlit with `python -m`
- It is for the provided relative imports to run
```bash
cd Langgraph/
python -m streamlit run core/frontend/streamlit_frontend.py
```
- And install mcp package of version<2
```bash
uv pip install "mcp<2"
```