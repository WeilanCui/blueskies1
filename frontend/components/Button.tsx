"use client";

import { Button as HeroUIButton } from "@heroui/react";
import type { ComponentProps } from "react";

type HeroUIButtonProps = ComponentProps<typeof HeroUIButton>;

export type AppButtonVariant = "primary" | "ghost";

export type ButtonProps = Omit<HeroUIButtonProps, "variant"> & {
  variant?: AppButtonVariant;
  disabled?: boolean;
};

const variantClass: Record<AppButtonVariant, string> = {
  primary: "primary-button",
  ghost: "ghost-button",
};

const heroVariant: Record<AppButtonVariant, NonNullable<HeroUIButtonProps["variant"]>> = {
  primary: "ghost",
  ghost: "ghost",
};

export function Button({
  variant = "primary",
  className,
  disabled,
  isDisabled,
  ...props
}: ButtonProps) {
  return (
    <HeroUIButton
      variant={heroVariant[variant]}
      className={["app-button", variantClass[variant], className].filter(Boolean).join(" ")}
      isDisabled={isDisabled ?? disabled}
      {...props}
    />
  );
}
