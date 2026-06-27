import { skinTypeOptions, toggleValue, type ProfileOption } from "../../lib/profileForm";

type SkinTypeSelectorProps = {
  values: string[];
  onChange: (values: string[]) => void;
  name: string;
  multiple?: boolean;
  options?: ProfileOption[];
  className?: string;
  optionClassName?: string;
};

export function SkinTypeSelector({
  values,
  onChange,
  name,
  multiple = false,
  options = skinTypeOptions,
  className,
  optionClassName,
}: SkinTypeSelectorProps) {
  return (
    <div className={className}>
      {options.map(([value, label]) => (
        <label className={optionClassName} key={value}>
          <input
            checked={values.includes(value)}
            name={name}
            type={multiple ? "checkbox" : "radio"}
            value={value}
            onChange={() => onChange(multiple ? toggleValue(values, value) : [value])}
          />
          <span>{label}</span>
        </label>
      ))}
    </div>
  );
}
