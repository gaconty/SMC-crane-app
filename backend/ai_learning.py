import pandas as pd
import numpy as np
import os
from datetime import datetime

# Try importing scikit-learn and joblib
try:
    import joblib
    from sklearn.ensemble import RandomForestRegressor
    AI_AVAILABLE = True
except ImportError:
    AI_AVAILABLE = False
    joblib = None

DATA_FILE = "calculation_history.csv"
MODEL_FILE = "crane_ai_model.pkl"

class SimpleKNN:
    def __init__(self, k=3):
        self.k = k
        self.X = None
        self.y = None
        self.X_min = None
        self.X_max = None

    def fit(self, X, y):
        self.X = X.to_numpy()
        self.y = y.to_numpy()
        # Min-Max Scaling parameters
        self.X_min = self.X.min(axis=0)
        self.X_max = self.X.max(axis=0)
        # Avoid division by zero
        self.X_max[self.X_max == self.X_min] += 1.0

    def predict(self, X_new):
        if self.X is None: return None
        
        # Normalize
        X_norm = (self.X - self.X_min) / (self.X_max - self.X_min)
        X_new_norm = (X_new.to_numpy() - self.X_min) / (self.X_max - self.X_min)
        
        predictions = []
        for x in X_new_norm:
            # Euclidean distance
            dists = np.linalg.norm(X_norm - x, axis=1)
            # Get k nearest indices
            k_idx = np.argsort(dists)[:self.k]
            # Average target values
            pred = self.y[k_idx].mean(axis=0)
            predictions.append(pred)
            
        return np.array(predictions)

    def save_state(self, filepath):
        import pickle
        state = {
            'k': self.k,
            'X': self.X,
            'y': self.y,
            'X_min': self.X_min,
            'X_max': self.X_max
        }
        with open(filepath, 'wb') as f:
            pickle.dump(state, f)

    def load_state(self, filepath):
        import pickle
        with open(filepath, 'rb') as f:
            state = pickle.load(f)
        self.k = state['k']
        self.X = state['X']
        self.y = state['y']
        self.X_min = state['X_min']
        self.X_max = state['X_max']

class CraneAILearning:
    def __init__(self):
        self.data_file = DATA_FILE
        self.model_file = MODEL_FILE
        self.model = None
        self.is_trained = False
        self.feature_cols = ['load_mass', 'radius', 'boom_len', 'slew_angle', 'soil_ks', 'cwt_mass', 'mat_L', 'mat_W']
        self._load_model()

    def _load_model(self):
        if os.path.exists(self.model_file):
            try:
                loaded_obj = joblib.load(self.model_file)
                if isinstance(loaded_obj, dict):
                    # It's a SimpleKNN state dict
                    self.model = SimpleKNN()
                    self.model.k = loaded_obj['k']
                    self.model.X = loaded_obj['X']
                    self.model.y = loaded_obj['y']
                    self.model.X_min = loaded_obj['X_min']
                    self.model.X_max = loaded_obj['X_max']
                else:
                    self.model = loaded_obj
                
                self.is_trained = True
            except:
                # Fallback load for SimpleKNN if joblib fails or not available
                try:
                    # Try loading as state dict first (New Way)
                    self.model = SimpleKNN()
                    self.model.load_state(self.model_file)
                    self.is_trained = True
                except:
                    # Try legacy pickle load (Old Way)
                    try:
                        import pickle
                        with open(self.model_file, 'rb') as f:
                            self.model = pickle.load(f)
                        self.is_trained = True
                    except Exception as e:
                        print(f"Failed to load model: {e}")

    def log_calculation(self, inputs: dict, outputs: dict):
        """
        Logs a calculation event.
        inputs: {load_mass, radius, boom_len, slew_angle, soil_ks, cwt_mass}
        outputs: {p_max, safety_factor}
        """
        record = {**inputs, **outputs, "timestamp": datetime.now().isoformat()}
        df = pd.DataFrame([record])
        
        if not os.path.exists(self.data_file):
            df.to_csv(self.data_file, index=False)
        else:
            df.to_csv(self.data_file, mode='a', header=False, index=False)

    def train_model(self):
        if not os.path.exists(self.data_file):
            return "No data to train on."
        
        try:
            df = pd.read_csv(self.data_file)
            if len(df) < 3:
                return f"Not enough data (Current: {len(df)}, Need: 3+)."
                
            # Features & Targets
            target_cols = ['p_max', 'safety_factor']
            
            # Check columns
            missing_feats = [c for c in self.feature_cols if c not in df.columns]
            if missing_feats:
                return f"Missing columns in history: {missing_feats}"
                
            X = df[self.feature_cols]
            y = df[target_cols].dropna()
            X = X.loc[y.index]
            
            if len(X) == 0:
                return "No valid data after cleaning."

            # Train
            if AI_AVAILABLE:
                self.model = RandomForestRegressor(n_estimators=100, random_state=42)
                self.model.fit(X, y)
                joblib.dump(self.model, self.model_file)
            else:
                # Fallback to SimpleKNN
                self.model = SimpleKNN(k=3)
                self.model.fit(X, y)
                # Save state instead of object to avoid pickling class issues
                self.model.save_state(self.model_file)
            
            self.is_trained = True
            return f"Success! Model trained on {len(X)} records ({'RandomForest' if AI_AVAILABLE else 'SimpleKNN'})."
        except Exception as e:
            return f"Training error: {str(e)}"

    def predict(self, inputs: dict):
        if not self.model or not self.is_trained:
            return None
            
        try:
            # Prepare input vector
            X_input = pd.DataFrame([inputs])[self.feature_cols]
            prediction = self.model.predict(X_input)
            
            # Handle different return shapes
            if isinstance(prediction, np.ndarray):
                 # SimpleKNN returns [[p_max, sf]]
                 # RF returns [[p_max, sf]]
                 val = prediction[0]
            else:
                 val = prediction[0]

            return {
                'p_max': val[0],
                'safety_factor': val[1]
            }
        except Exception as e:
            print(f"Prediction error: {e}")
            return None
            
    def get_history(self):
        if os.path.exists(self.data_file):
            return pd.read_csv(self.data_file)
        return pd.DataFrame()
