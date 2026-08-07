const ITEMS = [
  {
    icon: (
      <path d="M4 5h16v11H9l-4 4V5z" />
    ),
    title: "Say how it feels",
    body: "No genres. No decade sliders. Just the mood, in your own words.",
  },
  {
    icon: (
      <>
        <circle cx="10" cy="10" r="6" />
        <path d="M14.5 14.5L20 20M17 5l.6 1.4L19 7l-1.4.6L17 9l-.6-1.4L15 7l1.4-.6z" />
      </>
    ),
    title: "We search meaning, not metadata",
    body: "Your words are matched against what a film actually feels like to watch.",
  },
  {
    icon: (
      <>
        <path d="M4 6h16M4 12h16M4 18h10" />
        <circle cx="21" cy="18" r="2" />
      </>
    ),
    title: "A shortlist, with reasons",
    body: "A handful of picks, each with one line on why it fits — not a wall of results to sort through.",
  },
];

export function Explainer() {
  return (
    <section className="explainer">
      {ITEMS.map((item) => (
        <div key={item.title} className="explainer-item">
          <svg
            width="20"
            height="20"
            viewBox="0 0 24 24"
            fill="none"
            stroke="var(--color-accent)"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            className="explainer-icon"
          >
            {item.icon}
          </svg>
          <div className="explainer-title">{item.title}</div>
          <p className="text-muted explainer-body">{item.body}</p>
        </div>
      ))}
    </section>
  );
}
