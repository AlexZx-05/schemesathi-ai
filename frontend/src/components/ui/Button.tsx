import type { ButtonHTMLAttributes, ReactNode } from "react";
import { Link } from "react-router-dom";

type ButtonVariant = "primary" | "secondary" | "quiet";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant;
}

interface ButtonLinkProps {
  "aria-label"?: string;
  children: ReactNode;
  className?: string;
  to: string;
  variant?: ButtonVariant;
}

function buttonClassName(variant: ButtonVariant, className = "") {
  return `button button--${variant}${className ? ` ${className}` : ""}`;
}

export function Button({
  className,
  variant = "primary",
  ...props
}: ButtonProps) {
  return <button className={buttonClassName(variant, className)} {...props} />;
}

export function ButtonLink({
  "aria-label": ariaLabel,
  children,
  className,
  to,
  variant = "primary",
}: ButtonLinkProps) {
  return (
    <Link
      aria-label={ariaLabel}
      className={buttonClassName(variant, className)}
      to={to}
    >
      {children}
    </Link>
  );
}
