import os
import requests

GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
USERNAME = os.environ.get("GITHUB_USERNAME", "SantoshMane-Dev")

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        weeks {
          contributionDays {
            date
            contributionCount
            color
          }
        }
      }
    }
  }
}
"""

CELL = 13
GAP = 4
PADDING = 18
HEADER = 52
FOOTER = 30
SNAKE_LENGTH = 50
DURATION = 16


def fetch_calendar():
    response = requests.post(
        "https://api.github.com/graphql",
        json={"query": QUERY, "variables": {"login": USERNAME}},
        headers={
            "Authorization": f"Bearer {GITHUB_TOKEN}",
            "Content-Type": "application/json",
        },
        timeout=30,
    )
    response.raise_for_status()
    data = response.json()

    weeks = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]["weeks"]
    grid = []

    for week in weeks:
        column = []

        for day in week["contributionDays"]:
            column.append(
                {
                    "count": day["contributionCount"],
                    "color": day["color"],
                    "date": day["date"],
                }
            )

        grid.append(column)

    return grid


def center(x, y):
    return (
        PADDING + x * (CELL + GAP) + CELL / 2,
        HEADER + y * (CELL + GAP) + CELL / 2,
    )


def build_path(grid):
    empty = []

    for x, column in enumerate(grid):
        for y, day in enumerate(column):
            if day["count"] == 0:
                empty.append((x, y))

    if len(empty) < 12:
        empty = []

        for x, column in enumerate(grid):
            for y, day in enumerate(column):
                if day["count"] <= 1:
                    empty.append((x, y))

    if len(empty) < 12:
        empty = [(x, y) for x in range(len(grid)) for y in range(7)]

    remaining = set(empty)
    current = min(empty, key=lambda point: (point[1], point[0]))
    remaining.remove(current)
    path = [current]

    while remaining:
        next_point = min(
            remaining,
            key=lambda point: (
                abs(point[0] - current[0]) + abs(point[1] - current[1]),
                point[1],
                point[0],
            ),
        )

        remaining.remove(next_point)
        path.append(next_point)
        current = next_point

    return path


def route_data(path):
    if not path:
        return "M 20 70"

    commands = []
    previous = None

    for index, point in enumerate(path):
        cx, cy = center(*point)

        if index == 0:
            commands.append(f"M {cx:.1f} {cy:.1f}")
        else:
            px, py = center(*previous)

            if point[0] != previous[0] and point[1] != previous[1]:
                mid_x = (px + cx) / 2
                commands.append(f"L {mid_x:.1f} {py:.1f}")
                commands.append(f"L {mid_x:.1f} {cy:.1f}")

            commands.append(f"L {cx:.1f} {cy:.1f}")

        previous = point

    return " ".join(commands)


def render_svg(grid, snake_path):
    weeks = len(grid)
    width = PADDING * 2 + weeks * (CELL + GAP) - GAP
    height = HEADER + 7 * (CELL + GAP) - GAP + FOOTER
    route = route_data(snake_path)

    cells = []

    for x, column in enumerate(grid):
        for y, day in enumerate(column):
            count = day["count"]

            if count == 0:
                fill = "#161B22"
            elif count <= 2:
                fill = "#0E4429"
            elif count <= 4:
                fill = "#006D32"
            elif count <= 7:
                fill = "#26A641"
            else:
                fill = "#39D353"

            cx, cy = center(x, y)

            cells.append(
                f'<rect x="{cx - CELL / 2:.1f}" y="{cy - CELL / 2:.1f}" '
                f'width="{CELL}" height="{CELL}" rx="3" fill="{fill}"/>'
            )

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="GitHub contribution heatmap with animated snake">
  <defs>
    <linearGradient id="accent" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#EC4899"/>
      <stop offset="50%" stop-color="#8B5CF6"/>
      <stop offset="100%" stop-color="#0EA5E9"/>
    </linearGradient>
  </defs>

  <rect width="{width}" height="{height}" rx="14" fill="#0D1117"/>
  <rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="13" fill="none" stroke="#21262D" stroke-width="2"/>

  <text x="{width / 2}" y="30" text-anchor="middle" font-family="Segoe UI, Helvetica, Arial, sans-serif" font-size="16" font-weight="700" fill="#FFFFFF">CONTRIBUTION ACTIVITY</text>
  <rect x="{width / 2 - 65}" y="38" width="130" height="3" rx="1.5" fill="url(#accent)"/>

  {''.join(cells)}

  <path id="snakeRoute" d="{route}" fill="none" stroke="none" pathLength="1000"/>

  <path d="{route}" fill="none" stroke="#ffb2cd" stroke-width="10" stroke-linecap="round" stroke-linejoin="round" opacity="0.18"/>

  <path d="{route}" fill="none" stroke="#EC4899" stroke-width="8" stroke-linecap="round" stroke-linejoin="round" pathLength="1000" stroke-dasharray="{SNAKE_LENGTH} {1000 - SNAKE_LENGTH}">
    <animate
      attributeName="stroke-dashoffset"
      values="1000;0"
      dur="{DURATION}s"
      calcMode="linear"
      repeatCount="indefinite"
    />
  </path>

  <circle r="6" fill="#F472B6">
    <animateMotion
      dur="{DURATION}s"
      calcMode="linear"
      repeatCount="indefinite"
    >
      <mpath href="#snakeRoute" xlink:href="#snakeRoute"/>
    </animateMotion>
  </circle>

  <text x="{width / 2}" y="{height - 10}" text-anchor="middle" font-family="Segoe UI, Helvetica, Arial, sans-serif" font-size="10" fill="#8B949E">@{USERNAME} • contribution heatmap</text>
</svg>'''

    os.makedirs("output", exist_ok=True)

    with open("output/contribution-snake.svg", "w", encoding="utf-8") as file:
        file.write(svg)


def main():
    grid = fetch_calendar()
    snake_path = build_path(grid)
    render_svg(grid, snake_path)


if __name__ == "__main__":
    main()
