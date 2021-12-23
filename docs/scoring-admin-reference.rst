*******************************************
Scoring Admin Reference
*******************************************

This page gives a reference to all **scoretility** views which are available to
:term:`users <user>` who have the :term:`scoring admin` :term:`security role`.


.. _Club Affiliations view:

Club Affiliations view
=======================
**Navigation:** Scoring > Club Affiliations

For :term:`series` which have **Display Club Affiliation** set on the :ref:`Series view`, the club affiliation must match one of the
**Alternate Names** defined in this view. Note the **Display Name** and **Official Name** are automatically added to the 
**Alternate Names** list.

    :Display Name:
        short name for the club which is displayed on the relevant views
    
    :Official Name:
        official name for the club which shows up when the mouse hovers over the **Display Name**
    
    :Alternate Names:
        names which, when in the :term:`results`, map to this club. To add a new alternate name, simply type
        the name or paste the text, then hit carriage return

The **Copy from Year** button may be used to copy club affiliations from a previous year or another club.

.. image:: images/club-affiliations-view.*
    :align: center
    
.. image:: images/club-affiliations-edit.*
    :align: center
    

.. _Divisions view:

Divisions view
======================
**Navigation:** Scoring > Divisions

For each :term:`series` which has **Divisions** set to *yes*, there should be divisions set up on this view. 

    :Series:
        select the :term:`series` for which this :term:`division` is to apply to
    
    :Low Age:
        low age for this division

    :High Age:
        high age for this division

.. note:: The :term:`series` need to be set up before this view is used.

The **Copy from Year** button may be used to copy divisions from a previous year or another club.

.. image:: images/divisions-view.*
    :align: center
    
.. image:: images/divisions-edit.*
    :align: center



.. _Download Results view:

Download Results view
======================
**Navigation:** Scoring > Download Results

This view can be used to scrape results from a web page. The services which are supported are identified at the top of the
view.

For RunSignUp, one or more result sets can be combined into a single downloaded csv file. The file header may need to be
edited to be suitable for import using the :ref:`Races view` import function.

.. image:: images/download-results-view.*
    :align: center

When the URL is entered, additional fields are shown. The fields shown may depend on the service which holds the result
data (e.g., RunSignUp).
    
.. image:: images/download-results-loaded-view.*
    :align: center


.. _Edit Participants view:

Edit Participants view
=========================
**Navigation:** Scoring > Races > [next to race] **Import** or **✔** > **Choose File** / **Import**

**Navigation:** Scoring > Races > [next to race] **Import** or **✔** > Edit Participants

The import process finds members within the results, using a fuzzy logic to match names, e.g., member name John Doe for Result Name Jack Doe. 
The Match column indicates whether a match was found, and how close the match was

  * *definite* - name and age match exactly
  * *similar* - age matched, but name didn’t match exactly
  * *closeage* - age was close, but not exact
  * *missed* - nonmember series, runner not found in database

You should visit each entry that is *similar*, *closeage*, or *missed*

.. note:: 
  for races in series which allow nonmembers to run, the edit participants view may show a lot of *missed* results. Updating each of these individually as 
  described below may be time-consuming. For this reason there is a way to take all of these by bulk.

  * In the header, *Show All entries*. In the footer **verify all the entries are being shown before proceeding**

    * only entries which are "shown" will be updated in the next step, so this step is very important

  * Click **Tools ⛭**, then under **Select Names and Confirm** click **Confirm**
  * A progress bar will display. Before doing any other operations, be sure to wait until the progress bar disappears. 
    This can take a while - please be patient.
  * Once this is complete, continue as below for *similar* and *closeage* entries

By clicking in the **Match:** filter, you can limit your view to *similar*, *closeage*, and/or *missed*

* For results with Match of *similar*, *closeage*, or  *missed* there will be a pull-down under Standings Name. Here you can decide if the Result Name really 
  is for one of the member options
* Alternately, if you think you know the member you can click in the ⬜ on the left, then click **Edit** to modify the result. 
  This only works for members of the club for which the date of birth is known or estimated

  * In Result Name: start typing the name of the member and select, or just select from the pulldown
  * Age: and Gender: should automatically be filled in

  .. note:: 
      if you have filtered using Match, after editing you may need to reload page and apply your Match filter again. This is a bug 
      (`#209 <https://github.com/louking/rrwebapp/issues/209>`_) and will hopefully be fixed in a future release

* **Be sure to check the box under Confirm when you are satisfied the Standings Name is correct or "[not included]"**

In order for results to be included in :term:`series` standings, they must be tabulated. Near top of Edit Participants next to **Match:** field 
click **Tools ⛭**. Under Tabulate Results, click **Tabulate** (this step updates the standings)

.. image:: images/edit-participants-view.*
    :align: center

For :term:`series` which have **Display Club Affiliation** set on the :ref:`Series view`, the club affiliation must match one of the
**Alternate Names** defined in this view. If clubs are detected which are unknown, there will be a popup indicating which clubs were not
found. This must be resolved using the :ref:`Club Affiliations view`, adding these as **Alternate Names** and retabulating, or by editing 
the results file and reimporting.

.. image:: images/edit-participants-unknown-clubs.*
    :align: center



.. _Exclusions view:

Exclusions view
======================
**Navigation:** Scoring > Exclusions

Exclusions happen when using the :ref:`Edit Participants view`, and a name is suggested which is close to a result name, but
a different member name is chosen. This prevents the excluded **Member Name** from being offered for **Result Name** in the future

If an exclusion is made by accident, it may be deleted using this view.

.. image:: images/exclusions-view.*
    :align: center


.. _Members view:

Members view
======================
**Navigation:** Scoring > Members

For :term:`clubs <club>` that have :term:`members <member>`, this view provides a way to bring the current membership into the 
database.

If a service is set up (e.g., RunSignUp club service), the :term:`members <member>` list can be downloaded directly from the service.
Otherwise, a file needs to be imported into the system. The **Import** button is used to import the :term:`members <member>`.

.. image:: images/members-view.*
    :align: center

.. image:: images/members-import.*
    :align: center

.. _Races view:

Races view
======================
**Navigation:** Scoring > Members

This view is used to define the :term:`races <race>`, which must be done before :term:`results` are imported. Each :term:`race` can 
be entered individually, or a file of :term:`races <race>` can be imported.

    :Results:
        provides the **import** or **✔** action buttons

    :Race Name:
        name of the race
    
    :Date:
        date of the race
    
    :Miles:
        race distance in miles. For accurate age grading, the miles should be set with as much precision as possible, e.g.,

          * 5K - 3.10686 miles
          * 10K - 6.21371 miles
          * 15K - 9.32057 miles
          * Half marathon - 13.1094 miles
          * Marathon - 26.2188 miles
      
    :Surface:
        *road*, *track*, or *trail*

    :Series:
        one or more :term:`series` that this :term:`race` is included in

The view has the following filters:

    :Series:
        you can filter on :term:`races <race>` which are in one or more :term:`series` 

.. image:: images/races-view.*
    :align: center

.. image:: images/races-edit.*
    :align: center

To import :term:`races <race>`, click **Tools**, then choose a file for import.

.. image:: images/races-import.*
    :align: center

To import :term:`results` for a :term:`race`, click the **import** or **✔** button under the **Results** header. If the :term:`results` 
have already been imported the button is displayed as **✔**. Both buttons include navigation to the :ref:`Edit Participants view`. The **✔** 
button has additional navigation to the :ref:`Series Race Results view`.

From **import**

.. image:: images/races-race-import.*
    :align: center

From **✔**

.. image:: images/races-race-check.*
    :align: center


.. _Results Analysis Summary view:

Results Analysis Summary view
=================================
**Navigation:** Scoring > Results Analysis Summary

To be added

.. image:: images/results-analysis-summary-view.*
    :align: center

.. _Series view:

Series view
======================
**Navigation:** Scoring > Series

The Series view is used to describe the calculation for a series of :term:`races <race>`, in order to generate
standings for the :ref:`Standings view`.

    :Max Races:
        this is the max number of races which will count for the final standings result

    :Multiplier:
        this value is multiplied by the result score. Result score is determined by the remaining fields

    :Max Gen Points:
        set this if overall result score is determined by place. Points start with this value for the first place, 
        this value minus 1 for second place, etc. 
        
          * e.g., if **Max Gen Points** is set to 50, first place result score is 50, second place is 49, etc

    :Max Div Points:
        for this to work, this series must have Divisions set up. Set this if division result score is determined by place. 
        Points start with this value for the first place, this value minus 1 for second place, etc.

          * e.g., if **Max Div Points** is set to 10, first place result score is 10, second place is 19, etc
          * generally **Max Div Points** would be set to a lower number than **Max Gen Points**

    :Max by Num of Rnrs:
        set this to *yes* if the max should be determined by the number of runners who ran a race within a gender. Either set this, 
        or set **Max Gen Points** / **Max Div Points**, but not both

    :Order By:
        this can be set depending on how you’d like the results ordering to be shown

          * *time* to order by absolute time
          * *agtime* to order by age graded time
          * *agpercent* to order by age graded percent
          * *overallplace* to order by overall place

    :Order:
        this can be set depending on how you’d like the results ordering to be shown, *ascending* or *decending*

    :Members Only:
        set this to *yes* if the results import should only consider true members of a club

    :Avg Ties:
        set this to *yes* if ties should be averaged in order to determine result points

    :Overall:
        set this to *yes* if overall placement is to be calculated. Generally this only applies if **Max Gen Points** is set

    :Divisions:
        set this to *yes* only if division placement is to be calculated. Generally this only applies if **Max Div Points** is set. 
        Note Divisions must be set using :ref:`Divisions view` for this series for this to work properly.

    :Age Grade:
        set this to *yes* if age grade is to be calculated and used for result scoring. Generally this only applies if **Order By** is 
        set to *agtime* or *agpercent*

    :Place Min Races:
        minimum number of races to have run to be awarded a place
    
    :# OA Awards:
        number of overall awards to be emphasized

    :# Div Awards:
        number of division awards to be emphasized

    :Tiebreaker Options:
    
        * *Head to Head Point Differential*
  
          set to break tie by looking at points achieved at races run head to head
        
        * *Compare Average Points*

          set to break tie by looking at average points achieved for the top **Max Races** races
        
        * *Division Tie Compare Average Overall Points*
  
          set to break division tie by looking at average overall points achieved for the top **Max Races** races

    :Other Series Options:

        * *Proportional Scoring*
  
          check this if proportional scoring is to be used. Proportional scoring means top score gets 1 * **Multiplier**, and other
          scores get (top_time / this_time) * **Multiplier**

        * *Requires Club Affiliation*

          if this is checked, there must be a value in the club column which doesn't evaluate to *None* when compared against
          the :ref:`Club Affiliations view` data, otherwise the result doesn't get tabulated

        * *Display Club Affiliation*
  
          if this is checked, the club affiliation is displayed in the :ref:`Standings view` and :ref:`Series Race Results view`

    :Races:
        :term:`races <race>` can be added to the :term:`series` here or in the :ref:`Races view`

The **Copy from Year** button may be used to copy series from a previous year or another club.

.. image:: images/series-view.*
    :align: center


.. image:: images/series-edit.*
    :align: center


