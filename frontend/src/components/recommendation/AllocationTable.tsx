import type { InvestmentMode, PortfolioAllocation } from "../../types/recommendation.types";
import { formatInr, formatInrPrecise, formatPercent, formatUnits, holdingLabel } from "../../utils/displayFormatters";
import { AssetTypePill } from "./AssetTypePill";
import { seriesColorVar } from "./AllocationStackedBar";

interface AllocationTableProps {
  allocations: PortfolioAllocation[];
  investmentMode: InvestmentMode;
  amountColumnLabel: string;
}

export function AllocationTable({ allocations, investmentMode, amountColumnLabel }: AllocationTableProps) {
  const isOneTime = investmentMode === "one_time";
  const totalAmount = allocations.reduce((sum, a) => sum + a.amount, 0);
  const hasFunds = allocations.some((a) => a.asset_type === "mutual_fund");
  const hasStocks = allocations.some((a) => a.asset_type !== "mutual_fund");

  return (
    <div className="table-scroll">
      <table className="data-table">
        <thead>
          <tr>
            <th scope="col">Holding</th>
            <th scope="col" className="num">
              Weight
            </th>
            <th scope="col" className="num">
              {amountColumnLabel}
            </th>
            <th scope="col" className="num">
              {hasFunds && hasStocks ? "Price / NAV" : hasFunds ? "NAV" : "Last price"}
            </th>
            {isOneTime && (
              <th
                scope="col"
                className="num"
                title="Whole shares the amount buys at the last price; for funds, the units it buys at today's NAV"
              >
                {hasFunds && hasStocks ? "≈ Shares / units" : hasFunds ? "≈ Units" : "≈ Shares"}
              </th>
            )}
          </tr>
        </thead>
        <tbody>
          {allocations.map((allocation, index) => (
            <tr key={allocation.ticker}>
              <td>
                <div className="stock-cell">
                  <span className="swatch" style={{ background: seriesColorVar(index) }} aria-hidden="true" />
                  <div>
                    <div className="stock-cell__ticker">
                      {holdingLabel(allocation)}
                      <AssetTypePill assetType={allocation.asset_type} />
                    </div>
                    <div className="stock-cell__name">
                      {allocation.asset_type === "mutual_fund" ? allocation.sector : allocation.company_name}
                      {allocation.asset_type !== "mutual_fund" && allocation.sector ? ` · ${allocation.sector}` : ""}
                    </div>
                  </div>
                </div>
              </td>
              <td className="num">{formatPercent(allocation.weight_percent)}</td>
              <td className="num">{formatInr(allocation.amount)}</td>
              <td className="num">{formatInrPrecise(allocation.last_price)}</td>
              {isOneTime && <td className="num">{renderQuantity(allocation)}</td>}
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr>
            <th scope="row">Total</th>
            <td className="num">100%</td>
            <td className="num">{formatInr(totalAmount)}</td>
            <td />
            {isOneTime && <td />}
          </tr>
        </tfoot>
      </table>
    </div>
  );
}

function renderQuantity(allocation: PortfolioAllocation) {
  if (allocation.asset_type === "mutual_fund") {
    return allocation.approx_units != null ? `${formatUnits(allocation.approx_units)} units` : "—";
  }
  if (allocation.approx_whole_shares === 0) {
    return (
      <span className="text-warning" title="The allocation is less than the price of one share">
        0 ⚠
      </span>
    );
  }
  return allocation.approx_whole_shares;
}
