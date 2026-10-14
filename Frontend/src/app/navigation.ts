export const pages = {
  overview: {
    title: "Monitoramento de embarques",
    description: "Acompanhe viagens, plataformas e avisos aos passageiros.",
  },
  passengers: {
    title: "Passageiros",
    description: "Consulte passageiros e as notificações de cada viagem.",
  },
  events: {
    title: "Histórico de notificações",
    description: "Consulte os avisos registrados e seus destinatários.",
  },
} as const;
export type PageId = keyof typeof pages;
