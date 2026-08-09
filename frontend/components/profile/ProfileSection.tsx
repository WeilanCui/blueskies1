import { PencilSquareIcon } from "@heroicons/react/24/outline";
import type { ReactNode } from "react";

type ProfileSectionClassNames = {
  section: string;
  header: string;
  iconButton: string;
  display: string;
};

type ProfileSectionProps<SectionName extends string> = {
  section: SectionName;
  title: string;
  children: ReactNode;
  editingSection: SectionName | null;
  onEdit: (section: SectionName) => void;
  editor: ReactNode;
  classNames: ProfileSectionClassNames;
};

export function ProfileSection<SectionName extends string>({
  section,
  title,
  children,
  editingSection,
  onEdit,
  editor,
  classNames,
}: ProfileSectionProps<SectionName>) {
  const isEditing = editingSection === section;

  return (
    <article className={classNames.section}>
      <div className={classNames.header}>
        <h2>{title}</h2>
        <button
          aria-label={`Edit ${title.toLowerCase()}`}
          className={classNames.iconButton}
          type="button"
          onClick={() => onEdit(section)}
        >
          <PencilSquareIcon aria-hidden="true" />
        </button>
      </div>
      {isEditing ? (
        editor
      ) : (
        <div className={classNames.display}>{children}</div>
      )}
    </article>
  );
}
