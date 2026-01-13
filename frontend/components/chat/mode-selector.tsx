"use client";

import { useTranslations } from "next-intl";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Sparkles, MessageCircle, FileSearch } from "lucide-react";
import { SessionMode } from "@/lib/types";

interface ModeSelectorProps {
  currentMode: SessionMode;
  onModeChange: (mode: SessionMode) => void;
  hasDocuments: boolean;
  disabled?: boolean;
}

export function ModeSelector({
  currentMode,
  onModeChange,
  hasDocuments,
  disabled = false,
}: ModeSelectorProps) {
  const t = useTranslations("chat.mode");

  const modeIcons: Record<SessionMode, React.ReactNode> = {
    [SessionMode.AUTO]: <Sparkles className="h-4 w-4" />,
    [SessionMode.CHAT_ONLY]: <MessageCircle className="h-4 w-4" />,
    [SessionMode.RAG_ONLY]: <FileSearch className="h-4 w-4" />,
  };

  return (
    <div className="flex items-center gap-2">
      <span className="text-sm text-muted-foreground">{t("label")}:</span>
      <Select
        value={currentMode}
        onValueChange={(value) => onModeChange(value as SessionMode)}
        disabled={disabled}
      >
        <SelectTrigger className="w-[180px]">
          <SelectValue>
            <div className="flex items-center gap-2">
              {modeIcons[currentMode]}
              <span>{t(currentMode)}</span>
            </div>
          </SelectValue>
        </SelectTrigger>
        <SelectContent>
          <SelectItem value={SessionMode.AUTO}>
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4" />
              <span>{t("auto")}</span>
            </div>
          </SelectItem>
          <SelectItem value={SessionMode.CHAT_ONLY}>
            <div className="flex items-center gap-2">
              <MessageCircle className="h-4 w-4" />
              <span>{t("chatOnly")}</span>
            </div>
          </SelectItem>
          <SelectItem
            value={SessionMode.RAG_ONLY}
            disabled={!hasDocuments}
          >
            <div className="flex items-center gap-2">
              <FileSearch className="h-4 w-4" />
              <span>{t("ragOnly")}</span>
              {!hasDocuments && (
                <span className="text-xs text-muted-foreground ml-1">
                  ({t("noDocsRequired")})
                </span>
              )}
            </div>
          </SelectItem>
        </SelectContent>
      </Select>
    </div>
  );
}
