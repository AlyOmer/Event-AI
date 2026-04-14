"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { io, Socket } from "socket.io-client";

const SOCKET_URL = process.env.NEXT_PUBLIC_SOCKET_URL || "http://localhost:3001";

const SocketContext = createContext<Socket | null>(null);

export const useSocket = () => {
    return useContext(SocketContext);
};

export function SocketProvider({ children }: { children: React.ReactNode }) {
    const [socket, setSocket] = useState<Socket | null>(null);

    useEffect(() => {
        // Only connect if user has a valid auth token
        const token = typeof window !== 'undefined' ? localStorage.getItem('userToken') : null;

        if (!token) {
            // No token — don't establish socket connection
            return;
        }

        const socketInstance = io(SOCKET_URL, {
            autoConnect: false,
            auth: { token },
        });

        socketInstance.connect();
        setSocket(socketInstance);

        return () => {
            socketInstance.disconnect();
        };
    }, []);

    return (
        <SocketContext.Provider value={socket}>{children}</SocketContext.Provider>
    );
}
