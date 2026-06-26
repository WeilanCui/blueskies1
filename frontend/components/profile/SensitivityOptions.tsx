import { sensitivityOptions } from "../../lib/profileForm";

type SensitivityOptionsProps = {
  values: string[];
  onToggle: (value: string) => void;
  options?: string[];
  gridClassName?: string;
  optionClassName?: string;
};

export function SensitivityOptions({
  values,
  onToggle,
  options = sensitivityOptions,
  gridClassName,
  optionClassName,
}: SensitivityOptionsProps) {
  return (
    <div className={gridClassName}>
      {options.map((item) => (
        <label className={optionClassName} key={item}>
          <input
            checked={values.includes(item)}
            type="checkbox"
            onChange={() => onToggle(item)}
          />
          <span>{item}</span>
        </label>
      ))}
    </div>
  );
}
