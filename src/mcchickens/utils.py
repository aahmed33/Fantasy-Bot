def get_team_name(user):
    """
    Return a user's custom Sleeper team name.

    If no custom team name is set, use Sleeper's default
    naming convention: "Team <display_name>".
    """

    display_name = user.get("display_name", "Unknown")
    team_name = user.get("metadata", {}).get("team_name")

    if team_name:
        return team_name

    return f"Team {display_name}"