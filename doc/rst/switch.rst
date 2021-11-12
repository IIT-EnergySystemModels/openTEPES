``oT_Dict_SwitchingStage.csv`` Switching stage

``oT_Data_SwitchingStage.csv``             Line switching stages

IndBinLineCommit    Indicator of binary transmission switching decisions  {0 continuous, 1 binary}


Line switching stage
--------------------

A description of the data included in the file ``oT_Data_SwitchingStage.csv`` follows:

==========  ============  ==========  ========  ==================================================
Identifier  Header        Header      Header    Description
==========  ============  ==========  ========  ==================================================
Load level  Initial node  Final node  Circuit   Assignment of each load level to a switching stage
==========  ============  ==========  ========  ==================================================

This switching stage allows the definition of load levels assigned to a single stage and, consequently, the model will force to decide the same line switching decisions for all the load levels simultaneously. This is done
independently for each line.

Switching          The transmission line is able to switch on/off                                                                   Yes/No
