import type { ComponentPropsWithoutRef, ElementType, ReactNode } from "react";
import styles from "./Panel.module.css";

export type PanelVariant = "default" | "form" | "results" | "notice";

type PanelOwnProps = {
  as?: ElementType;
  variant?: PanelVariant;
  split?: boolean;
  error?: boolean;
  className?: string;
  children?: ReactNode;
};

export type PanelProps<T extends ElementType = "section"> = PanelOwnProps &
  Omit<ComponentPropsWithoutRef<T>, keyof PanelOwnProps>;

function panelClassName({
  variant = "default",
  split = false,
  error = false,
  className,
}: Pick<PanelOwnProps, "variant" | "split" | "error" | "className">) {
  return [
    styles.panel,
    styles[variant],
    split && styles.split,
    error && styles.error,
    className,
  ]
    .filter(Boolean)
    .join(" ");
}

export function Panel<T extends ElementType = "section">({
  as,
  variant = "default",
  split = false,
  error = false,
  className,
  children,
  ...props
}: PanelProps<T>) {
  const Component = (as ?? "section") as ElementType;

  return (
    <Component
      className={panelClassName({ variant, split, error, className })}
      {...props}
    >
      {children}
    </Component>
  );
}
