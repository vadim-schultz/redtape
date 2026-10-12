import { Button, HStack, IconButton } from "@chakra-ui/react";
import { FaEnvelope, FaGoogle, FaRegUser } from "react-icons/fa";
import { Link } from "react-router-dom";

import KeyValueRow from "../../ui/KeyValueRow";
import { useLocale } from "../../../contexts/LocaleContext";
import { useAuth } from "../../../features/auth/contexts/AuthContext";

/** Profile controls: sign-in icons or user plus sign-out. */
export default function ProfileMenuRow() {
  const { status, signOut } = useAuth();
  const { t } = useLocale();

  if (status === "unconfigured" || status === "loading") return null;

  return (
    <KeyValueRow label={t("menu.profile")}>
      {status === "anonymous" ? (
        <HStack gap="1">
          <IconButton variant="ghost" size="sm" asChild>
            <Link to="/login" aria-label={t("auth.sign_in_with_email")}>
              <FaEnvelope data-icon="envelope" aria-hidden="true" />
            </Link>
          </IconButton>
          <IconButton variant="ghost" size="sm" asChild>
            <Link to="/login" aria-label={t("auth.sign_in_with_google")}>
              <FaGoogle data-icon="google" aria-hidden="true" />
            </Link>
          </IconButton>
        </HStack>
      ) : (
        <HStack gap="2">
          <FaRegUser data-icon="user" aria-hidden="true" />
          <Button size="sm" variant="ghost" onClick={() => void signOut()}>
            {t("auth.sign_out")}
          </Button>
        </HStack>
      )}
    </KeyValueRow>
  );
}
