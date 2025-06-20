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
        return

    # Integrate GoogleNewsFetcher
    from fetcher import GoogleNewsFetcher
    search_string = config.get("search_string", "Chelsea FC")
    lookback_days = config.get("lookback_days", 1)
    language = config.get("language", "en")
    fetcher = GoogleNewsFetcher(search_string=search_string, lookback_days=lookback_days, language=language)
    stories = fetcher.fetch()
    print(f"Fetched {len(stories)} stories:")
    for story in stories:
        print(f"- {story.title} ({story.url}) [{story.source}]")

if __name__ == "__main__":
    main()
