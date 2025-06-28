import React from "react";
import PropTypes from 'prop-types';

UserContextProvider.propTypes = {
    children: PropTypes.node.isRequired
};

export const UserDataContext = React.createContext()

function UserContextProvider ({children}){ 

    const [userData, setUserData] = React.useState(null)
    return(
        <UserDataContext.Provider value={{userData, setUserData}}>
            {children}
        </UserDataContext.Provider>
    )
}

export default UserContextProvider;