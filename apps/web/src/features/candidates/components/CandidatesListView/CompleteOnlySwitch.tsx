import { Switch } from "@chakra-ui/react";

import { useLocale } from "../../../../contexts/LocaleContext";

export interface CompleteOnlySwitchProps {
  checked: boolean;
  onChange: (checked: boolean) => void;
}

/** On narrows the list to candidates with all five flags; off shows every candidate. */
export default function CompleteOnlySwitch({
  checked,
  onChange,
}: CompleteOnlySwitchProps) {
  const { t } = useLocale();

  return (
    <Switch.Root
      checked={checked}
      onCheckedChange={({ checked: next }) => onChange(next)}
    >
      <Switch.HiddenInput />
      <Switch.Control>
        <Switch.Thumb />
      </Switch.Control>
      <Switch.Label>{t("candidates.complete_only")}</Switch.Label>
    </Switch.Root>
  );
}
