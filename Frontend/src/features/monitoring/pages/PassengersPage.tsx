import { Icon } from "@/shared/ui/Icon";
import { labels } from "../model/constants";
import type { BoardingEvent } from "../model/types";
import type { PassengerFilter, PassengerItem } from "../model/selectors";
import styles from "./PassengersPage.module.css";
import common from "@/shared/ui/Panel.module.css";

export function PassengersPage({
  passengers,
  search,
  passengerFilter,
  onSearch,
  onStatusFilter,
  onSelect,
}: {
  passengers: PassengerItem[];
  search: string;
  passengerFilter: PassengerFilter;
  onSearch: (query: string) => void;
  onStatusFilter: (filter: PassengerFilter) => void;
  onSelect: (event: BoardingEvent) => void;
}) {
  return (
    <section className={styles["passenger-section"]}>
      <div className={common["section-heading"]}>
        <h2>Lista de passageiros</h2>
        <span>{passengers.length} resultados</span>
      </div>
      <div className={styles["search-row"]}>
        <label className={styles["search-field"]}>
          <Icon name="search" size={17} />
          <input
            aria-label="Buscar passageiro, código ou destino"
            placeholder="Buscar passageiro, código ou destino"
            value={search}
            onChange={(event) => onSearch(event.target.value)}
          />
        </label>
        <select
          aria-label="Filtrar status de notificação"
          value={passengerFilter}
          onChange={(event) =>
            onStatusFilter(event.target.value as PassengerFilter)
          }
        >
          <option value="all">Todos os status</option>
          <option value="notified">Com notificações</option>
          <option value="waiting">Sem notificações</option>
        </select>
      </div>
      <div className={styles["table-scroll"]}>
        <table>
          <thead>
            <tr>
              <th>Passageiro</th>
              <th>Destino / assento</th>
              <th>Última notificação</th>
            </tr>
          </thead>
          <tbody>
            {passengers.map(({ passenger, bus, last }) => {
              return (
                <tr key={passenger.passenger_code}>
                  <td>
                    <div className={styles["passenger-name"]}>
                      <span className={common["avatar"]}>
                        {passenger.name
                          .split(" ")
                          .slice(0, 2)
                          .map((name) => name[0])
                          .join("")}
                      </span>
                      <div>
                        <strong>{passenger.name}</strong>
                        <small>{passenger.passenger_code}</small>
                      </div>
                    </div>
                  </td>
                  <td>
                    <strong>{bus?.itinerary.to ?? passenger.bus_code}</strong>
                    <small>
                      {passenger.bus_code} · Assento {passenger.seat}
                    </small>
                  </td>
                  <td>
                    {last ? (
                      <button
                        className={styles["notification-link"]}
                        onClick={() => onSelect(last)}
                      >
                        <Icon name="check" size={14} />
                        {labels[last.event]}
                      </button>
                    ) : (
                      <span className={common["muted"]}>Sem notificações</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
      {!passengers.length && (
        <div className={common["empty-state"]}>
          <h3>Nenhum passageiro encontrado</h3>
          <p>Revise a busca ou os filtros selecionados.</p>
        </div>
      )}
    </section>
  );
}
