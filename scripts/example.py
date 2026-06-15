def get_messages() -> list[str]:
    """Return the messages printed by the practice script."""
    return ["Hello, Codex!", "This is a practice script."]


def main() -> None:
    for message in get_messages():
        print(message)


if __name__ == "__main__":
    main()
