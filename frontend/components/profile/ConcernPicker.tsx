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
  input?: string;
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
            {section.items.map((item) => (
              <label className={classNames?.option} key={item.value}>
                <input
                  className={classNames?.input}
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
