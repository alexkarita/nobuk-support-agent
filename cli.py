"""CLI chat with the support agent."""
from agent import chat


def main():
    print("Nobuk Support Agent (type 'quit' to exit)\n")
    while True:
        user = input("You: ").strip()
        if user.lower() in {"quit", "exit"}:
            break
        if not user:
            continue
        try:
            print(f"Agent: {chat('cli', user)}\n")
        except Exception as e:
            print(f"Agent: Sorry, something went wrong ({type(e).__name__}: {e})\n")


if __name__ == "__main__":
    main()