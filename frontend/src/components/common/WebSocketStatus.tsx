"use client";

import { Badge } from "@/components/ui/badge";
import { Wifi, WifiOff } from "lucide-react";

interface WebSocketStatusProps {
  isConnected: boolean;
  showLabel?: boolean;
}

export function WebSocketStatus({ isConnected, showLabel = true }: WebSocketStatusProps) {
  if (isConnected) {
    return (
      <Badge variant="outline" className="bg-green-500/10 text-green-700 border-green-500/20">
        <Wifi className="h-3 w-3 mr-1.5" />
        {showLabel && "Conectado"}
        {!showLabel && <span className="h-2 w-2 rounded-full bg-green-500 animate-pulse" />}
      </Badge>
    );
  }

  return (
    <Badge variant="outline" className="bg-red-500/10 text-red-700 border-red-500/20">
      <WifiOff className="h-3 w-3 mr-1.5" />
      {showLabel && "Desconectado"}
      {!showLabel && <span className="h-2 w-2 rounded-full bg-red-500" />}
    </Badge>
  );
}
