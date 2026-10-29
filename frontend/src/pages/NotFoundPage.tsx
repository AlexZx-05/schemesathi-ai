import { ButtonLink } from "../components/ui/Button";

export function NotFoundPage() {
  return (
    <section aria-labelledby="not-found-title" className="page page--narrow">
      <p className="eyebrow">404 · Page not found</p>
      <h1 className="page-title" id="not-found-title">
        This page isn’t here.
      </h1>
      <p className="page-intro">
        The link may be outdated, or the page may have moved.
      </p>
      <ButtonLink to="/">Return home</ButtonLink>
    </section>
  );
}
