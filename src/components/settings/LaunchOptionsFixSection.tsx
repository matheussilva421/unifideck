import { FC } from "react";
import { PanelSection, PanelSectionRow, ButtonItem } from "@decky/ui";
import { useTranslation } from "react-i18next";
import { useRPCMutation } from "../../api/useRPC";
import { rpcRoutes } from "../../api/rpc-routes";
import { useToast } from "../../hooks/useToast";

interface FixResult {
  fixed: number;
}

export const LaunchOptionsFixSection: FC = () => {
  const { t } = useTranslation();
  const toast = useToast();
  const { mutate, loading, error } = useRPCMutation<[], FixResult>(
    rpcRoutes.fixLaunchOptionsOrdering,
  );

  const handleClick = async () => {
    const result = await mutate();
    if (!result) {
      toast.error(
        t("toasts.launchOptionsFixFailed"),
        error?.message ?? t("errors.unknown"),
      );
      return;
    }
    if (result.fixed === 0) {
      toast.info(
        t("toasts.launchOptionsFixNoop"),
        t("toasts.launchOptionsFixNoopMessage"),
      );
    } else {
      toast.success(
        t("toasts.launchOptionsFixSuccess"),
        t("toasts.launchOptionsFixSuccessMessage", {
          count: result.fixed,
        }),
      );
    }
  };

  return (
    <PanelSection title={t("launchOptionsFix.title")}>
      <PanelSectionRow>
        <ButtonItem layout="below" onClick={handleClick} disabled={loading}>
          {loading
            ? t("launchOptionsFix.fixing")
            : t("launchOptionsFix.fixAll")}
        </ButtonItem>
      </PanelSectionRow>
    </PanelSection>
  );
};
