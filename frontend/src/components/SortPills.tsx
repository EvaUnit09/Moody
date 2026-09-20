export type SortOption = "best-match" | "highest-rated" | "newest" | "title-az";

interface SortPillsProps {
  selectedSort: SortOption;
  onSortChange: (sort: SortOption) => void;
}

const sortLabels: Record<SortOption, string> = {
  "best-match": "Best match",
  "highest-rated": "Highest rated",
  "newest": "Newest",
  "title-az": "Title A–Z",
};

const sortOptions: SortOption[] = ["best-match", "highest-rated", "newest", "title-az"];

export function SortPills({ selectedSort, onSortChange }: SortPillsProps) {
  return (
    <div className="sort-pills" role="radiogroup" aria-label="Sort results">
      {sortOptions.map((option) => (
        <button
          key={option}
          type="button"
          role="radio"
          aria-checked={selectedSort === option}
          onClick={() => onSortChange(option)}
          className={`sort-pill ${selectedSort === option ? "sort-pill-active" : ""}`}
        >
          {sortLabels[option]}
        </button>
      ))}
    </div>
  );
}
