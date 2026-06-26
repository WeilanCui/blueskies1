import { type ConcernSection, toggleValue } from "../../lib/profileForm";
import styles from "./ConcernPicker.module.css";

type ConcernPickerProps = {
  values: string[];
  onChange: (values: string[]) => void;
  sections: ConcernSection[];
  variant?: "card" | "pill";
};

export function ConcernPicker({
  values,
  onChange,
  sections,
  variant = "card",
}: ConcernPickerProps) {
  const optionClass =
    variant === "pill" ? styles.pillOption : styles.cardOption;

  return (
    <div className={styles.stack}>
      {sections.map((section) => (
        <fieldset className={styles.fieldset} key={section.title}>
          <legend>{section.title}</legend>
          <div className={styles.grid}>
            {section.items.map((item) => (
              <label className={optionClass} key={item.value}>
                <input
                  className={styles.visuallyHiddenInput}
                  checked={values.includes(item.value)}
                  type="checkbox"
                  onChange={() => onChange(toggleValue(values, item.value))}
                />
                <span>{item.label}</span>
              </label>
            ))}
          </div>
        </fieldset>
      ))}
    </div>
  );
}
