import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import tensorflow as tf

# import local 
from signals_processing import *


## == Set a fixed random seed value, for reproducibility
SEED = 1337
np.random.seed(SEED)
#~ tf.random.set_seed(SEED)

## == Load data

# number of samples per movement
num_samples = 119

# dictonory of movements and corresponding filenames
gestures = {
    "punch": "../data/punch.csv",
    "flex": "../data/flex.csv",
}

# number of gestures
n_gestures = len(gestures)

## == create a one-hot encoded matrix that is used in the output
# matrix representation of response: for example for 'punch' we got [1,0]
one_hot_gestures = np.eye(n_gestures)


## == Start loading data
inputs = []
outputs = []
ts = []

# labels of data with ranges of sensors for normalization: label:[min:max]
labels = {"aX":[-4,4], 
          "aY":[-4,4],
          "aZ":[-4,4], 
          "gX":[-2000,2000], 
          "gY":[-2000,2000],
          "gZ":[-2000,2000]}


# open files and collect data to inputs and outputs
for ind, gst in enumerate(gestures):
    
    # open file as dataframe
    df = pd.read_csv(gestures[gst])
    # ouput vector for gesture, ex.: [0,1]
    out = one_hot_gestures[ind]
    # number of recordings in file
    num_recordings = int(df.shape[0] /num_samples)
    
    for i in range(num_recordings):
        # take single recording and process it to vector for input using  
        # Sample_arduino() object from signal_processing.py
        smpl = Sample_arduino(df,i*num_samples,(i+1)*num_samples,labels=labels)
        
        # get a 1D vector of data for recording
        tnsr = smpl.get_data_vector()
        
        # collect inputs and outputs
        inputs.append(tnsr.squeeze().tolist())
        outputs.append(out)
    
    

# |||| === Below is part of the code from colab with some modification |||||||
# vvvv =============================================================== vvvvvvv

# convert the list to numpy array
inputs = np.array(inputs)
outputs = np.array(outputs)


print("Data set parsing and preparation complete.")


# Randomize the order of the inputs, so they can be evenly distributed for training, testing, and validation
# https://stackoverflow.com/a/37710486/2020087
num_inputs = len(inputs)
randomize = np.arange(num_inputs)
np.random.shuffle(randomize)

# Swap the consecutive indexes (0, 1, 2, etc) with the randomized indexes
inputs = inputs[randomize]
outputs = outputs[randomize]

# Split the recordings (group of samples) into three sets: training, testing and validation
TRAIN_SPLIT = int(0.6 * num_inputs)
TEST_SPLIT = int(0.2 * num_inputs + TRAIN_SPLIT)

inputs_train, inputs_test, inputs_validate = np.split(inputs, [TRAIN_SPLIT, TEST_SPLIT])
outputs_train, outputs_test, outputs_validate = np.split(outputs, [TRAIN_SPLIT, TEST_SPLIT])

print("Data set randomization and splitting complete.")

## == Build the model and train it
model = tf.keras.Sequential()
model.add(tf.keras.layers.Dense(50, activation='relu')) # relu is used for performance
model.add(tf.keras.layers.Dense(15, activation='relu'))
model.add(tf.keras.layers.Dense(n_gestures, activation='softmax')) # softmax is used, because we only expect one gesture to occur per input
model.compile(optimizer='rmsprop', loss='mse', metrics=['mae'])
history = model.fit(inputs_train, outputs_train, epochs=600, batch_size=1, validation_data=(inputs_validate, outputs_validate))

## ==  Verify

# graph the loss, the model above is configure to use "mean squared error" as the loss function
loss = history.history['loss']
val_loss = history.history['val_loss']
epochs = range(1, len(loss) + 1)

# skip first epoches for plotting for simplicity of graph
SKIP = 100
plt.plot(epochs[SKIP:], loss[SKIP:], 'g.', label='Training loss')
plt.plot(epochs[SKIP:], val_loss[SKIP:], 'b.', label='Validation loss')
plt.title('Training and validation loss')
plt.xlabel('Epochs')
plt.ylabel('Loss')
plt.legend()




# graph of mean absolute error
mae = history.history['mae']
val_mae = history.history['val_mae']
plt.plot(epochs[SKIP:], mae[SKIP:], 'g.', label='Training MAE')
plt.plot(epochs[SKIP:], val_mae[SKIP:], 'b.', label='Validation MAE')
plt.title('Training and validation mean absolute error')
plt.xlabel('Epochs')
plt.ylabel('MAE')
plt.legend()

# use the model to predict the test inputs
predictions = model.predict(inputs_test)

# print the predictions and the expected ouputs
print("predictions =\n", np.round(predictions, decimals=3))
print("actual =\n", outputs_test)

# Plot the predictions along with to the test data
plt.clf()
plt.title('Training data predicted vs actual values')
plt.plot(inputs_test, outputs_test, 'b.', label='Actual')
plt.plot(inputs_test, predictions, 'r.', label='Predicted')


plt.show()


# Convert the model to the TensorFlow Lite format without quantization
converter = tf.lite.TFLiteConverter.from_keras_model(model)
tflite_model = converter.convert()

# Save the model to disk
with open("../models/gesture_model.tflite", "wb") as f:
    f.write(tflite_model)


