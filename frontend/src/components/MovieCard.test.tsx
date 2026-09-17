import { describe, expect, test } from "vitest";
import { render, screen } from "@testing-library/react";
import { MovieCard } from "./MovieCard";
import type { MovieRecommendation } from "../api";

const MOCK_MOVIE: MovieRecommendation = {
  tmdb_id: 550,
  title: "Fight Club",
  poster_path: "/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg",
  year: 1999,
  vote_average: 8.4,
  genres: ["Drama", "Thriller"],
  reason: "A darkly philosophical exploration of masculinity",
  providers: [],
};

describe("MovieCard", () => {
  test("renders movie title, year, genres, reason, and rating", () => {
    render(<MovieCard movie={MOCK_MOVIE} />);

    expect(screen.getByText("Fight Club")).toBeInTheDocument();
    expect(screen.getByText("1999")).toBeInTheDocument();
    expect(screen.getByText("Drama")).toBeInTheDocument();
    expect(screen.getByText("Thriller")).toBeInTheDocument();
    expect(
      screen.getByText(/A darkly philosophical exploration/),
    ).toBeInTheDocument();
    expect(screen.getByText("8.4")).toBeInTheDocument();
  });

  test("renders poster image when poster_path available", () => {
    render(<MovieCard movie={MOCK_MOVIE} />);

    const img = screen.getByAltText("Fight Club poster");
    expect(img).toHaveAttribute(
      "src",
      "https://image.tmdb.org/t/p/w342/pB8BM7pdSp6B6Ih7QZ4DrQ3PmJK.jpg",
    );
  });

  test("renders placeholder when poster_path is null", () => {
    const movieWithoutPoster = { ...MOCK_MOVIE, poster_path: null };
    render(<MovieCard movie={movieWithoutPoster} />);

    expect(screen.getByText("No poster")).toBeInTheDocument();
  });

  test("renders watch provider logos when providers available", () => {
    const movieWithProviders = {
      ...MOCK_MOVIE,
      providers: [
        {
          name: "Netflix",
          logo_url: "https://image.tmdb.org/t/p/original/netflix.png",
          link: "https://www.themoviedb.org/movie/550/watch",
        },
        {
          name: "Prime Video",
          logo_url: "https://image.tmdb.org/t/p/original/prime.png",
          link: "https://www.themoviedb.org/movie/550/watch",
        },
      ],
    };

    render(<MovieCard movie={movieWithProviders} />);

    const netflixLogo = screen.getByAltText("Netflix");
    expect(netflixLogo).toHaveAttribute(
      "src",
      "https://image.tmdb.org/t/p/original/netflix.png",
    );
    expect(netflixLogo).toHaveClass("provider-logo");

    const primeLogo = screen.getByAltText("Prime Video");
    expect(primeLogo).toHaveAttribute(
      "src",
      "https://image.tmdb.org/t/p/original/prime.png",
    );
  });

  test("renders provider links with correct attributes", () => {
    const movieWithProviders = {
      ...MOCK_MOVIE,
      providers: [
        {
          name: "Netflix",
          logo_url: "https://image.tmdb.org/t/p/original/netflix.png",
          link: "https://www.themoviedb.org/movie/550/watch",
        },
      ],
    };

    render(<MovieCard movie={movieWithProviders} />);

    const link = screen.getByTitle("Watch on Netflix");
    expect(link).toHaveAttribute(
      "href",
      "https://www.themoviedb.org/movie/550/watch",
    );
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", "noopener noreferrer");
  });

  test("renders provider name fallback when logo_url is null", () => {
    const movieWithProviders = {
      ...MOCK_MOVIE,
      providers: [
        {
          name: "Paramount+",
          logo_url: null,
          link: "https://www.themoviedb.org/movie/550/watch",
        },
      ],
    };

    render(<MovieCard movie={movieWithProviders} />);

    expect(screen.getByText("Paramount+")).toBeInTheDocument();
    expect(screen.getByText("Paramount+")).toHaveClass("provider-name");
  });

  test("does not render provider section when providers empty", () => {
    render(<MovieCard movie={MOCK_MOVIE} />);

    // Provider section should not exist
    const card = screen.getByText("Fight Club").closest(".movie-card");
    expect(card?.querySelector(".movie-card-providers")).not.toBeInTheDocument();
  });

  test("does not crash when providers undefined", () => {
    const movieWithoutProviders = { ...MOCK_MOVIE, providers: undefined };
    render(<MovieCard movie={movieWithoutProviders as any} />);

    expect(screen.getByText("Fight Club")).toBeInTheDocument();
  });

  test("renders up to 3 providers only", () => {
    const movieWithManyProviders = {
      ...MOCK_MOVIE,
      providers: [
        {
          name: "Netflix",
          logo_url: "https://image.tmdb.org/t/p/original/netflix.png",
          link: "https://www.themoviedb.org/movie/550/watch",
        },
        {
          name: "Prime Video",
          logo_url: "https://image.tmdb.org/t/p/original/prime.png",
          link: "https://www.themoviedb.org/movie/550/watch",
        },
        {
          name: "Hulu",
          logo_url: "https://image.tmdb.org/t/p/original/hulu.png",
          link: "https://www.themoviedb.org/movie/550/watch",
        },
        {
          name: "Disney+",
          logo_url: "https://image.tmdb.org/t/p/original/disney.png",
          link: "https://www.themoviedb.org/movie/550/watch",
        },
      ],
    };

    render(<MovieCard movie={movieWithManyProviders} />);

    expect(screen.getByAltText("Netflix")).toBeInTheDocument();
    expect(screen.getByAltText("Prime Video")).toBeInTheDocument();
    expect(screen.getByAltText("Hulu")).toBeInTheDocument();
    expect(screen.queryByAltText("Disney+")).toBeInTheDocument();
  });

  test("does not render reason when not provided", () => {
    const movieWithoutReason = { ...MOCK_MOVIE, reason: undefined };
    render(<MovieCard movie={movieWithoutReason as any} />);

    expect(screen.getByText("Fight Club")).toBeInTheDocument();
    expect(
      screen.queryByText(/A darkly philosophical exploration/),
    ).not.toBeInTheDocument();
  });

  test("TMDB link opens in new tab", () => {
    render(<MovieCard movie={MOCK_MOVIE} />);

    const posterLink = screen
      .getByAltText("Fight Club poster")
      .closest("a") as HTMLAnchorElement;
    expect(posterLink).toHaveAttribute("target", "_blank");
    expect(posterLink).toHaveAttribute("rel", "noopener noreferrer");
    expect(posterLink).toHaveAttribute(
      "href",
      "https://www.themoviedb.org/movie/550",
    );
  });
});
