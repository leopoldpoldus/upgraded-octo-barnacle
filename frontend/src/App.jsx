import {useState, useEffect} from 'react'
import './App.css'
import generateAnswer from './components/GPT3_API.jsx';
import RecordVoice from "./components/RecordVoice.jsx";

const App = () => {

    return (
        <div>
            <RecordVoice/>
        </div>
    );
};

export default App;

