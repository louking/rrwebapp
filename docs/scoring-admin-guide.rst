===========================================
Scoring Admin Guide
===========================================

Introduction
===========================================

This guide describes the concepts of the **scoretility** Scoring Module, and gives guidance on
how to achieve the work flow.

This document describes how to administer **scoretility**, a race results database. **scoretility** gives a club the ability to define various race series, 
which races are in each series, and to collect and tabulate results for races run. When results are tabulated, standings are made available showing 
the current scores for all the athletes included in that series. For more information, see https://scoretility.com/features.

In order to follow these instructions, you must be a :term:`scoring admin` for **scoretility**. If you need admin privileges for **scoretility**, contact 
the FSRC Chief Technology Dude at technology@steeplechasers.org to be added.

License
===========================================

See https://github.com/louking/rrwebapp/blob/master/README.md#license for details on **scoretility** licensing.

Use Cases
===========================================

General
-------------------------------------------

* To do any administration for scoretility results, you need to be logged in. See :ref:`Log In`.
* For best security, the first time you log in, you should change your password. See :ref:`Change Password`.
* Make sure correct club and year are set in header

Beginning of Year Setup
-------------------------------------------
* Create series, most likely :ref:`copy series from previous year`
* Create divisions, most likely :ref:`copy divisions from previous year`
* Create each race
  
  * A few things to note:
  
    * You’ll probably have to ask around for specific dates of races. If you don’t know the date for a race, add “(date TBD)” to the race name
    * Make sure you have the exact specific number of miles listed for each race. This is for age grade calculations and needs to be very precise.
    * For FSRC, there needs to be two races listed for the decathlon 800m – one that is part of the grand prix and equalizer series, and a separate 
      one that is just part of the decathlon series. The one that is part of the decathlon series is open to all runners while the one that is part 
      of the grand prix and equalizer series is members-only. I.e., we don’t want nonmembers to be included in the grand prix and equalizer standings, 
      but we do want them to be included in the decathlon standing.

FSRC Racing Team Management
-------------------------------------------
* At the scoretility Home page, in the upper right corner, set the date to the current year and the club name to the FSRC Racing Team
* If a racing team member has run a race which is not already in scoretility’s database, the race must be added. See :ref:`Add Race`.

  * When updating the “series” the race is in
  
    * Always click All Races
    * If this race is not on the racing team schedule click Other Races

* Once a race is in the scoretility database, results may be added. Often an individual result would be added, e.g., from the 
  FSRC Racing Team Information Submission Form (Responses) sheet. See :ref:`Add Individual Result`.
* Sometimes there are many racing team members who have run a race. In this case it might be easier to import the results file to 
  include all their results. See :ref:`Add Results From File`.

Basic flow
================

This section shows the basic flow which is required each year, and for importing and tabulating the results for a race.

..
   see https://www.graphviz.org/
   see http://graphs.grevian.org/

New Year
----------------

.. graphviz::

   digraph records {
        graph [fontname = "helvetica"];
        node [fontname = "helvetica"];
        edge [fontname = "helvetica"];
        "Series view" -> "Divisions view"[label="divisions"];
        "Series view" -> "Series view"[label="create series"];
        "Divisions view" -> "Races view";
        "Divisions view" -> "Divisions view"[label="create divisions"];
        "Series view" -> "Races view"[label="no divisions"];
        "Races view" -> "Races view"[label="create races"];
    }

Results Management
-----------------------

.. graphviz::

    digraph records {
         graph [fontname = "helvetica"];
         node [fontname = "helvetica"];
         edge [fontname = "helvetica"];
         "Races view" -> "Edit Participants view"[label="import results"];
         "Edit Participants view" -> "Edit Participants view"[label="resolve missing and similar results"];
         "Edit Participants view" -> "Series Race Results view"[label="tabulate"]
     }
 
Detailed Operations
===========================================

.. _Log In:

Log In
-------------------------------------------
Follow these instructions to log in to scoretility.

* Go to the scoretility home page at scoretility.com 
* Click the log in link in the upper right
* Enter email address and password

.. _Change Password:

Change Password
-------------------------------------------
The internet is a dangerous place, and there are constantly people trying to break into the steeplechasers web site and scoretility. 
**Please pick a secure password, with capitals, lower case, numbers and special characters, at least 8 characters.**

* Click on ⛭ near the log out link
* Enter new Password
* Click **Update** 

.. _Add Series:

Add Series
-------------------------------------------

Races must be part of a series to be tabulated. Generally it’s better to add the series before adding the race. Follow these instructions to add a series.

.. _Copy Series from Previous Year:

Copy Series from Previous Year (needs update)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
If the series for this club have been set up in a prior year, follow these instructions to copy all the series from the previous year. Do this first before adding a new series for the year. 

* Make sure year and club are set correctly in the scoretility header
* Click Series in navigation menu
* Click **Tools ⛭**, then under Copy Series > Copy from Year, Select year to copy from, then click **Copy**

Add Series from Scratch
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
If the series for this club have never been set up, follow these instructions to add each series.

* Make sure year and club are set correctly in the scoretility header
* Click Series in navigation menu
* Click Add + near the top of the table
* Give the series a name. 
  
  .. note::
    because of some processing later, it is very important that the name is distinct from other series, i.e., the words in one series name 
    cannot be found in another series name
  
* The following series attributes may be set, depending on how you want the series standings to work
  
  * Max Races - this is the max number of races which will count for the final standings result
  * Multiplier - this value is multiplied by the result score. Result score is determined by the remaining fields
  * Max Gender Points - set this if overall result score is determined by place. Points start with this value for the first place, 
    this value minus 1 for second place, etc.
  
    * e.g., if Max Gender Points is set to 50, first place result score is 50, second place is 49, etc
  
  * Max Division Points - for this to work, this series must have Divisions set up. Set this if division result score is determined by place. 
    Points start with this value for the first place, this value minus 1 for second place, etc.

    * e.g., if Max Division Points is set to 10, first place result score is 10, second place is 19, etc
    * generally Max Division Points would be set to a lower number than Max Gender Points
  
  * Max by Number of Runners - check this if the max should be determined by the number of runners who ran a race within a gender. Either set this, 
    or set Max Gender Points/Max Division Points, but not both
  * Order By - this can be set depending on how you’d like the results ordering to be shown
  * Order - this can be set depending on how you’d like the results ordering to be shown
  * Members Only - check this box if the results import should only consider true members of a club
  * Average Ties - check this if ties should be averaged in order to determine result points
  * Calculate Overall - check this if overall placement is to be calculated. Generally this only applies if Max Gender Points is set
  * Calculate Divisions - check this only if division placement is to be calculated. Generally this only applies if Max Division Points is set. 
    Note Divisions must be set for this series for this to work properly.
  * Calculate Age Grade - check this if age grade is to be calculated and used for result scoring. Generally this only applies if Order By is 
    set to agtime or agpercent

  * If races were set up before series, Races in this Series can be used to set which races are included in the series by checking them here. 
    Otherwise, when you set up or add a race later, you can check the series that race is included in.


.. _Add Divisions:

Add Divisions
-------------------------------------------
Series optionally use divisions as part of the tabulation process. 


.. _Copy Divisions from Previous Year:

Copy Divisions from Previous Year (needs update)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
If the divisions for this club have been set up in a prior year, follow these instructions to copy all the divisions from a previous year. 
Do this first before adding new divisions for the series. 

* Make sure year and club are set correctly in the scoretility header
* Make sure series have been set up as in Add Series
* Click Divisions in navigation menu
* Click **Tools ⛭**, then under Copy Divisions > Copy from Year, Select year to copy from, then click **Copy**

Add Divisions from Scratch
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
If the divisions for this club have never been set up, follow these instructions to add divisions for each series.

* Make sure year and club are set correctly in the scoretility header
* Make sure series have been set up as in Add Series
* Click Divisions in navigation menu
* Click **New** near the top of the table
* Repeat for each age range
  
  * Choose a series 
  * Set age range for this division
  * Click **Create**

  
.. _Add Race:

Add Race
-------------------------------------------
Follow these instructions to add a race.

* Make sure year and club are set correctly in the scoretility header
* Click Races in navigation menu
* Click **New** near the top of the table
* Enter the race name, date, surface and distance. For most accurate age grading, use the following distances for non-integral mile races. 
  (Chief Technology Dude admits to being anal about this)

  * 5K - 3.10686 miles
  * 10K - 6.21371 miles
  * Half marathon - 13.1094 miles
  * Marathon - 26.2188 miles
  
* Click on the “series” the race will be in
* Click **Create**


.. _Edit Results:

Edit Results
-------------------------------------------
The main point of scoretility is to add results to the database and to update series standings through tabulation of these results. Results can be 
added from a file when all the results for a race are added at once, or individually, in cases when only a few results need to be added.

.. _Add Results from File:

Add Results from File
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Follow these instructions to add results from a race results file. Import files must follow the format defined 
at https://scoretility.com/doc/importresults (note xls and xlsx files are allowed as well).

* Make sure year and club are set correctly in the scoretility header
* Click Races in navigation menu
* In the Results column, it will either say **import** or **✔**.
  
  * Click **import** or **✔**
  * Click Choose File then navigate to the file to be imported
  * Click **Open** 
  * Click **Import** 
  
* If there are already results in the race, you will be asked Overwrite results? 
  
  .. note::
    any results previously entered into the race will be overwritten

  * This is normally ok because the results from the file are the “official” results
  * Click **Overwrite** 
  
* You will be put into the Edit Participants view
  
  * The import process finds members within the results, using a fuzzy logic to match names, e.g., member name John Doe for Result Name Jack Doe. 
  * The Match column indicates whether a match was found, and how close the match was

    * *definite* - name and age match exactly
    * *similar* - age matched, but name didn’t match exactly
    * *missed* - age was close, but not exact

* Edit each entry that is *similar* or *missed*

  .. note::
    races for series which allow nonmembers to run the edit results window may have a lot of *missed* results. Updating each of these individually as 
    described below may be time-consuming. For this reason there is a way to take all of these by bulk.

    * In the header, Show All entries. In the footer verify all the entries are being shown before proceeding
    * Click **Tools ⛭**, then under Select Names and Confirm click **Confirm**
    * A progress bar will display. Before doing any other operations, be sure to wait until the progress bar disappears. 
      This can take quite a while - maybe 30 minutes for automatic selection of 400+ entries.
    * Once this is complete, continue as below for *similar* entries

  * By clicking in the **Match:** text box, you can limit your view to *similar* and/or *missed*
  * For results with Match of *similar* or  *missed* there will be a pull-down under Standings Name. Here you can decide if the Result Name really 
    is for one of the member options
  * Alternately, if you think you know the member you can click in the ⬜ on the left, then click **Edit** to modify the result. 
    This only works for members of the club for which the date of birth is known or estimated

    * In Result Name: start typing the name of the member and select, or just select from the pulldown
    * Age: and Gender: should automatically be filled in
  
    .. note:: 
        if you have filtered using Match, after editing, you may need to reload page and apply your Match filter again. This is a bug (issue #209) 
        and will hopefully be fixed in a future release

  * **Be sure the checkbox under Confirm is checked when you are satisfied the Standings Name is correct or [not included]**
  
* Near top of Edit Participants next to **Match:** field click **Tools ⛭** 
* Under Tabulate Results, click **Tabulate** (this step updates the standings)

.. _Add Individual Result:

Add Individual Result
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Follow these instructions to add an individual result. Note if you import results from a file later, this individual result will be lost.

* Make sure year and club are set correctly in the scoretility header
* Click Races in navigation menu
* In the Results column, it will either say **import** or **✔**
  
  * Click **import** or **✔**, then click **Edit Participants** 
  
* In the table header, near the left, click **New** 

  * In Result Name: start typing the name of the member and select, or just select from the pulldown
  * Age: and Gender: should automatically be filled in

* Type in the Time:. Formats which should work are HH:MM:SS, MM:SS and maybe SS (not sure about this last one)
  
* let Chief Technology Dude know if any of these don’t work

* No need to fill in Hometown: or Club:
* Click **Create** 
* Near top of Edit Participants next to Match: field click **Tools ⛭** 
* Under Tabulate Results, click **Tabulate** (this step updates the standings)
