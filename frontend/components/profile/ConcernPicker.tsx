import {
  concernSections,
  toggleValue,
  type ConcernSection,
} from "../../lib/profileForm";

type ConcernPickerClassNames = {
  stack?: string;
  fieldset?: string;
  grid?: string;
  option?: string;
};

type ConcernPickerProps = {
  values: string[];
  onChange: (values: string[]) => void;
  sections?: ConcernSection[];
  classNames?: ConcernPickerClassNames;
};

export function ConcernPicker({
  values,
  onChange,
  sections = concernSections,
  classNames,
}: ConcernPickerProps) {
  return (
    <div className={classNames?.stack}>
      {sections.map((section) => (
        <fieldset className={classNames?.fieldset} key={section.title}>
          <legend>{section.title}</legend>
          <div className={classNames?.grid}>
            {section.items.map(([value, label]) => (
              <label className={classNames?.option} key={value}>
                <input
                  checked={values.includes(value)}
                  type="checkbox"
                  onChange={() => onChange(toggleValue(values, value))}
                />
                <span>{label}</span>
              </label>
            ))}
          </div>
        </fieldset>
      ))}
    </div>
  );
}
