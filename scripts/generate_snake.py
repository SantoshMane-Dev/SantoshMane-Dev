import math
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

# ---------- layout ----------
CELL = 13
GAP = 4
PADDING = 18
HEADER = 52
FOOTER = 30

# ---------- snake ----------
SNAKE_SEGMENTS = 7        # total body blocks (head + tail) -> short snake
SPEED = 180               # pixels per second (higher = faster)
# head -> tail colours (bright lime to deep green, matches GitHub greens)
SNAKE_COLORS = ["#E75480", "#FF69B4", "#FFB6C1", "#FFD1DC", " #F8C8DC", "#FFF0F5", "#FFFFFF"]

# GitHub dark-theme greens
LEVELS = [
    (0, "#161B22"),
    (2, "#0E4429"),
    (4, "#006D32"),
    (7, "#26A641"),
    (10**9, "#39D353"),
]


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
    return [
        [
            {"count": d["contributionCount"], "color": d["color"], "date": d["date"]}
            for d in week["contributionDays"]
        ]
        for week in weeks
    ]


def center(x, y):
    return (
        PADDING + x * (CELL + GAP) + CELL / 2,
        HEADER + y * (CELL + GAP) + CELL / 2,
    )


def build_path(grid):
    empty = [(x, y) for x, col in enumerate(grid) for y, d in enumerate(col) if d["count"] == 0]

    if len(empty) < 12:
        empty = [(x, y) for x, col in enumerate(grid) for y, d in enumerate(col) if d["count"] <= 1]

    if len(empty) < 12:
        empty = [(x, y) for x in range(len(grid)) for y in range(7)]

    remaining = set(empty)
    current = min(empty, key=lambda p: (p[1], p[0]))
    remaining.remove(current)
    path = [current]

    while remaining:
        nxt = min(
            remaining,
            key=lambda p: (abs(p[0] - current[0]) + abs(p[1] - current[1]), p[1], p[0]),
        )
        remaining.remove(nxt)
        path.append(nxt)
        current = nxt

    return path


def route_points(path):
    """Pixel points of the route; diagonal jumps become right-angle turns."""
    points = []
    previous = None

    for index, point in enumerate(path):
        cx, cy = center(*point)

        if index > 0:
            px, py = center(*previous)
            if point[0] != previous[0] and point[1] != previous[1]:
                mid_x = (px + cx) / 2
                points.append((mid_x, py))
                points.append((mid_x, cy))

        points.append((cx, cy))
        previous = point

    return points


def route_data(points):
    if not points:
        return "M 20 70", 1.0

    d = [f"M {points[0][0]:.1f} {points[0][1]:.1f}"]
    length = 0.0

    for (x0, y0), (x1, y1) in zip(points, points[1:]):
        d.append(f"L {x1:.1f} {y1:.1f}")
        length += math.hypot(x1 - x0, y1 - y0)

    return " ".join(d), max(length, 1.0)


def cell_color(count):
    for limit, color in LEVELS:
        if count <= limit:
            return color
    return LEVELS[-1][1]


def snake_body(duration, step_time):
    """Tail is drawn first, head last so the head sits on top."""
    parts = []

    for i in reversed(range(SNAKE_SEGMENTS)):
        color = SNAKE_COLORS[min(i, len(SNAKE_COLORS) - 1)]
        size = 11.5 - i * 0.7          # body tapers towards the tail
        half = size / 2
        # each block trails the one in front (negative begin = already running,
        # so shift by a full loop minus the delay to place it BEHIND the head)
        begin = -(duration - i * step_time)
        opacity = 1.0 - i * 0.07

        if i == 0:
            # head: slightly bigger, faces direction of travel, with eyes
            parts.append(
                f'''<g filter="url(#glow)">
    <g>
      <rect x="-7" y="-7" width="14" height="14" rx="5" fill="{color}"/>
      <circle cx="2.5" cy="-3" r="1.9" fill="#0D1117"/>
      <circle cx="2.5" cy="3" r="1.9" fill="#0D1117"/>
      <circle cx="3" cy="-3" r="0.6" fill="#FFFFFF"/>
      <circle cx="3" cy="3" r="0.6" fill="#FFFFFF"/>
      <animateMotion dur="{duration:.2f}s" begin="{begin:.2f}s" repeatCount="indefinite" rotate="auto">
        <mpath href="#snakeRoute" xlink:href="#snakeRoute"/>
      </animateMotion>
    </g>
  </g>'''
            )
        else:
            parts.append(
                f'''<g filter="url(#glow)" opacity="{opacity:.2f}">
    <rect x="{-half:.1f}" y="{-half:.1f}" width="{size:.1f}" height="{size:.1f}" rx="3.5" fill="{color}">
      <animateMotion dur="{duration:.2f}s" begin="{begin:.2f}s" repeatCount="indefinite">
        <mpath href="#snakeRoute" xlink:href="#snakeRoute"/>
      </animateMotion>
    </rect>
  </g>'''
            )

    return "\n  ".join(parts)


def render_svg(grid, snake_path):
    weeks = len(grid)
    width = PADDING * 2 + weeks * (CELL + GAP) - GAP
    height = HEADER + 7 * (CELL + GAP) - GAP + FOOTER

    route, length = route_data(route_points(snake_path))
    duration = length / SPEED
    step_time = (CELL + GAP - 5) / SPEED  # tight spacing -> compact body

    cells = []
    for x, column in enumerate(grid):
        for y, day in enumerate(column):
            cx, cy = center(x, y)
            cells.append(
                f'<rect x="{cx - CELL / 2:.1f}" y="{cy - CELL / 2:.1f}" '
                f'width="{CELL}" height="{CELL}" rx="3" fill="{cell_color(day["count"])}"/>'
            )

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="GitHub contribution heatmap with animated snake">
  <defs>
    <linearGradient id="accent" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#17692F"/>
      <stop offset="50%" stop-color="#39D353"/>
      <stop offset="100%" stop-color="#C6FF7A"/>
    </linearGradient>
    <filter id="glow" x="-100%" y="-100%" width="300%" height="300%">
      <feGaussianBlur stdDeviation="1.6" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>
  </defs>

  <rect width="{width}" height="{height}" rx="14" fill="#0D1117"/>
  <rect x="1" y="1" width="{width - 2}" height="{height - 2}" rx="13" fill="none" stroke="#21262D" stroke-width="2"/>

  <text x="{width / 2}" y="30" text-anchor="middle" font-family="Segoe UI, Helvetica, Arial, sans-serif" font-size="16" font-weight="700" fill="#E6EDF3">CONTRIBUTION ACTIVITY</text>
  <rect x="{width / 2 - 65}" y="38" width="130" height="3" rx="1.5" fill="url(#accent)"/>

  {''.join(cells)}

  <path id="snakeRoute" d="{route}" fill="none" stroke="none"/>

  {snake_body(duration, step_time)}

  <text x="{width / 2}" y="{height - 10}" text-anchor="middle" font-family="Segoe UI, Helvetica, Arial, sans-serif" font-size="10" fill="#8B949E">@{USERNAME} \u2022 contribution heatmap</text>
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
