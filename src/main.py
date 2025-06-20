# Main entry point for the News Aggregator

def main() -> None:
    print("News Aggregator starting up...")
    # Example: Load config
    try:
        from config_loader import load_config
        config = load_config()
        print("Loaded config:", config)
    except Exception as e:
        print("Config load failed:", e)

if __name__ == "__main__":
    main()
