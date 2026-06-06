import Image from "next/image";

import { cn } from "@/lib/utils";

type CompanyLogoProps = {
  className?: string;
  variant?: "light" | "default";
  priority?: boolean;
};

export function CompanyLogo({ className, variant = "light", priority = false }: CompanyLogoProps) {
  const src = variant === "light" ? "/optimal-group-logo-light.png" : "/optimal-group-logo.png";

  return (
    <Image
      src={src}
      alt="Optimal Group"
      width={320}
      height={92}
      priority={priority}
      className={cn("h-9 w-auto max-w-full object-contain object-left sm:h-10", className)}
      data-testid="company-logo"
    />
  );
}
