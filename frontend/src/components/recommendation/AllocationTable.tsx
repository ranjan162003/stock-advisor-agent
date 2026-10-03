import type { InvestmentMode, StockAllocation } from "../../types/recommendation.types";
import { formatInr, formatInrPrecise, formatPercent, shortTicker } from "../../utils/displayFormatters";
import { seriesColorVar } from "./AllocationStackedBar";

interface AllocationTableProps {
  allocations: StockAllocation[];
  investmentMode: InvestmentMode;
  amountColumnLabel: string;
}

export function AllocationTable({ allocations, investmentMode, amountColumnLabel }: AllocationTableProps) {
  const isOneTime = investmentMode === "one_time";
  const totalAmount = allocations.reduce((sum, a) => sum + a.amount, 0);

  return (
    <div className="table-scroll">
      <table className="data-table">
        <thead>
          <tr>
            <th scope="col">Stock</th>
            <th scope="col" className="num">
              Weight
            </th>
            <th scope="col" className="num">
              {amountColumnLabel}
            </th>
            <th scope="col" className="num">
              Last price
            </th>
            {isOneTime && (
              <th scope="col" className="num" title="Whole shares that the rupee amount can buy at the last price">
                ≈ Shares
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
                    <div className="stock-cell__ticker">{shortTicker(allocation.ticker)}</div>
                    <div className="stock-cell__name">
                      {allocation.company_name}
                      {allocation.sector ? ` · ${allocation.sector}` : ""}
                    </div>
                  </div>
                </div>
              </td>
              <td className="num">{formatPercent(allocation.weight_percent)}</td>
              <td className="num">{formatInr(allocation.amount)}</td>
              <td className="num">{formatInrPrecise(allocation.last_price)}</td>
              {isOneTime && (
                <td className="num">
                  {allocation.approx_whole_shares === 0 ? (
                    <span className="text-warning" title="The allocation is less than the price of one share">
                      0 ⚠
                    </span>
                  ) : (
                    allocation.approx_whole_shares
                  )}
                </td>
              )}
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
