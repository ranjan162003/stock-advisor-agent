import type { AssetType } from "../../types/recommendation.types";

interface AssetTypePillProps {
  assetType?: AssetType;
}

/** Small "MF" tag next to mutual funds; stocks need no tag. */
export function AssetTypePill({ assetType }: AssetTypePillProps) {
  if (assetType !== "mutual_fund") return null;
  return (
    <span className="asset-pill" title="Mutual fund">
      MF
    </span>
  );
}
