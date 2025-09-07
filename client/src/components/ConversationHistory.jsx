import React, { useEffect, useState } from 'react';
import { useDispatch, useSelector } from 'react-redux';
import { fetchConversations, setActiveConversation, fetchMessages, startNewChat, deleteConversation } from '../redux/convoSlice';
import { Button } from "@/components/ui/button";
import { PlusCircle, X } from 'lucide-react';
import {
    AlertDialog,
    AlertDialogAction,
    AlertDialogCancel,
    AlertDialogContent,
    AlertDialogDescription,
    AlertDialogFooter,
    AlertDialogHeader,
    AlertDialogTitle,
    AlertDialogTrigger,
} from "@/components/ui/alert-dialog";

const ConversationHistory = ({ jwt }) => {
    const dispatch = useDispatch();
    const { conversations, activeConversationId, status } = useSelector(state => state.conversation);
    const [isDeleting, setIsDeleting] = useState(false);

    useEffect(() => {
        if (jwt) {
            dispatch(fetchConversations(jwt));
        }
    }, [dispatch, jwt]); //fetch conversations whenever jwt changes

    const handleConversationClick = (id) => {
        dispatch(setActiveConversation(id));
        dispatch(fetchMessages({ conversationId: id, jwt }));
    };

    const handleNewChat = () => {
        dispatch(startNewChat());
    };

    const handleDeleteConversation = async (convoId) => {
        setIsDeleting(true);
        try {
            await dispatch(deleteConversation({ conversationId: convoId, jwt })).unwrap();
            //if the deleted conversation was active, start a new chat
            if (activeConversationId === convoId) {
                dispatch(startNewChat());
            }
        } catch (error) {
            console.error("Failed to delete conversation:", error);
        } finally {
            setIsDeleting(false);
        }
    };

    return (
        <div className="flex flex-col p-4 gap-2 h-full">
            <Button onClick={handleNewChat} className="flex items-center justify-start gap-2 bg-cyan-600 hover:bg-cyan-700">
                <PlusCircle className="w-5 h-5" />
                <span>New Chat</span>
            </Button>
            <h2 className="text-lg font-semibold text-gray-300 mt-4 px-2">History</h2>
            <div className="flex flex-col gap-1 overflow-y-auto flex-1">
                {status === 'loading' && conversations.length === 0 ? (
                    //skeleton loader for initial load
                    Array.from({ length: 5 }).map((_, i) => (
                        <div key={i} className="h-10 bg-gray-700 rounded-md animate-pulse w-full"></div>
                    ))
                ) : (
                    conversations.map(convo => (
                        <div key={convo.$id} className="relative flex items-center group">
                            <Button
                                variant={activeConversationId === convo.$id ? "secondary" : "ghost"}
                                className={`w-full justify-start truncate pr-8  ${activeConversationId === convo.$id ?
                                "text-black" : "text-gray-400"}`}
                                onClick={() => handleConversationClick(convo.$id)}
                            >
                                {convo.title}
                            </Button>
                            <AlertDialog>
                                <AlertDialogTrigger asChild>
                                    <Button
                                        variant="secondary"
                                        size="icon"
                                        className="absolute right-0 top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity text-gray-800 hover:text-red-500 hover:bg-white"
                                        disabled={isDeleting}
                                    >
                                        <X className="w-4 h-4" />
                                    </Button>
                                </AlertDialogTrigger>
                                <AlertDialogContent className="bg-[#0a1a1f] border-cyan-950 text-white">
                                    <AlertDialogHeader>
                                        <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
                                        <AlertDialogDescription className="text-gray-400">
                                            This action cannot be undone. This will permanently delete your
                                            conversation and all its messages.
                                        </AlertDialogDescription>
                                    </AlertDialogHeader>
                                    <AlertDialogFooter>
                                        <AlertDialogCancel className="bg-gray-700 text-white hover:bg-gray-600 border-none">Cancel</AlertDialogCancel>
                                        <AlertDialogAction 
                                            onClick={() => handleDeleteConversation(convo.$id)}
                                            className="bg-red-600 text-white hover:bg-red-700"
                                        >
                                            Delete
                                        </AlertDialogAction>
                                    </AlertDialogFooter>
                                </AlertDialogContent>
                            </AlertDialog>
                        </div>
                    ))
                )}
            </div>
        </div>
    );
};

export default ConversationHistory;