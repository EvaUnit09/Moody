import { useState } from "react";

interface ShareButtonProps {
  query: string;
}

export function ShareButton({ query }: ShareButtonProps) {
  const [showCopied, setShowCopied] = useState(false);

  async function handleShare() {
    const url = new URL(window.location.href);
    url.search = `?q=${encodeURIComponent(query)}`;
    const shareUrl = url.toString();

    if (navigator.share) {
      try {
        await navigator.share({
          title: "Moody - Movie Recommendation",
          text: `Movies for: "${query}"`,
          url: shareUrl,
        });
      } catch (err) {
        if (err instanceof Error && err.name !== "AbortError") {
          console.error("Share failed:", err);
        }
      }
    } else {
      try {
        await navigator.clipboard.writeText(shareUrl);
        setShowCopied(true);
        setTimeout(() => setShowCopied(false), 2000);
      } catch (err) {
        console.error("Copy failed:", err);
      }
    }
  }

  return (
    <button
      type="button"
      className="btn btn-secondary share-btn"
      onClick={handleShare}
      aria-label="Share results"
      title="Share these results"
    >
      <svg
        width="16"
        height="16"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
        aria-hidden="true"
      >
        <circle cx="18" cy="5" r="3" />
        <circle cx="6" cy="12" r="3" />
        <circle cx="18" cy="19" r="3" />
        <line x1="8.59" y1="13.51" x2="15.42" y2="17.49" />
        <line x1="15.41" y1="6.51" x2="8.59" y2="10.49" />
      </svg>
      <span>{showCopied ? "Copied!" : "Share"}</span>
    </button>
  );
}
